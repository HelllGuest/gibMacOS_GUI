"""
gibMacOS GUI
https://github.com/HelllGuest/gibMacOS_GUI

Original gibMacOS by corpnewt: https://github.com/corpnewt/gibMacOS
macrecovery.py by acidanthera team: https://github.com/acidanthera/OpenCorePkg

GUI Author: Anoop Kumar
License: MIT
"""

import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from .exceptions import CancelledError, ProgramError

# Ensure Scripts import works when run directly
# Get the project root directory (two levels up from this file)
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(current_file)
src_dir = os.path.dirname(backend_dir)
project_root = os.path.dirname(src_dir)
scripts_path = os.path.join(project_root, "gibMacOS", "Scripts")

# Add scripts path to sys.path if not already there
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

try:
    import plist  # type: ignore[reportMissingImports]
    import run  # type: ignore[reportMissingImports]

    import downloader
    from gibMacOS.Scripts import utils  # Use the original gibMacOS Utils class
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print(f"Make sure the Scripts directory exists at: {scripts_path}")
    sys.exit(1)


class GibMacOSBackend:
    """Backend class for handling macOS installer downloads and catalog management."""

    def __init__(
        self,
        update_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        cancel_event: Optional[Any] = None,
    ) -> None:
        """Initialize the backend with callbacks and event."""
        # Initialize core components
        self.downloader = downloader.Downloader(interactive=False)
        self.utils = utils.Utils("gibMacOSGUI", interactive=False)
        self.runner = run.Run()

        # Callbacks and events
        self.update_callback = update_callback
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event

        # File paths
        self.settings_path = os.path.join(
            project_root, "gibMacOS", "Scripts", "settings.json"
        )
        self.prod_cache_path = os.path.join(
            project_root, "gibMacOS", "Scripts", "prod_cache.plist"
        )

        # Load settings
        self.settings = self._load_settings()

        # Load product cache
        self.prod_cache = self._load_prod_cache()

        # Configuration
        self.current_macos = self.settings.get("current_macos", 20)
        self.min_macos = 5
        self.current_catalog = self.settings.get("current_catalog", "publicrelease")
        self.find_recovery = self.settings.get("find_recovery", False)
        self.caffeinate_downloads = self.settings.get("caffeinate_downloads", True)
        self.save_local = self.settings.get("save_local", False)
        self.force_local = self.settings.get("force_local", False)

        # Data storage
        self.catalog_data = None
        self.mac_prods = []
        self.caffeinate_process = None

        # Catalog configuration
        self.catalog_suffix = {
            "public": "beta",
            "publicrelease": "",
            "customer": "customerseed",
            "developer": "seed",
        }

        # macOS version mappings
        self.mac_os_names_url = {
            "8": "mountainlion",
            "7": "lion",
            "6": "snowleopard",
            "5": "leopard",
        }

        # Recovery package suffixes
        self.recovery_suffixes = ("RecoveryHDUpdate.pkg", "RecoveryHDMetaDmg.pkg")

        # Settings to persist
        self.settings_to_save = (
            "current_macos",
            "current_catalog",
            "find_recovery",
            "caffeinate_downloads",
            "save_local",
            "force_local",
        )

    def _load_settings(self):
        """Load settings from JSON file."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _load_prod_cache(self):
        """Load product cache from plist file."""
        if os.path.exists(self.prod_cache_path):
            try:
                with open(self.prod_cache_path, "rb") as f:
                    cache_data = plist.load(f)
                    if isinstance(cache_data, dict):
                        return cache_data
            except (IOError, ValueError):
                pass
        return {}

    def _update_status(self, message):
        if self.update_callback:
            self.update_callback(message)

    def _update_progress(self, current, total, start_time):
        if self.progress_callback:
            self.progress_callback(current, total, start_time)

    def save_settings(self):
        for setting in self.settings_to_save:
            self.settings[setting] = getattr(self, setting, None)
        try:
            json.dump(self.settings, open(self.settings_path, "w"), indent=2)
        except Exception as e:
            raise ProgramError(
                "Failed to save settings to:\n\n{}\n\nWith error:\n\n - {}\n".format(
                    self.settings_path, repr(e)
                ),
                title="Error Saving Settings",
            )

    def save_prod_cache(self):
        try:
            with open(self.prod_cache_path, "wb") as f:
                plist.dump(self.prod_cache, f)
        except Exception as e:
            raise ProgramError(
                "Failed to save product cache to:\n\n{}\n\nWith error:\n\n - {}\n".format(
                    self.prod_cache_path, repr(e)
                ),
                title="Error Saving Product Cache",
            )

    def set_catalog(self, catalog):
        self.current_catalog = (
            catalog.lower()
            if catalog.lower() in self.catalog_suffix
            else "publicrelease"
        )

    def num_to_macos(self, macos_num, for_url=True):
        if for_url:
            return (
                self.mac_os_names_url.get(str(macos_num), "10.{}".format(macos_num))
                if macos_num <= 16
                else str(macos_num - 5)
            )
        return "10.{}".format(macos_num) if macos_num <= 15 else str(macos_num - 5)

    def macos_to_num(self, macos):
        try:
            macos_parts = [int(x) for x in macos.split(".")][
                : 2 if macos.startswith("10.") else 1
            ]
            if macos_parts[0] == 11:
                macos_parts = [10, 16]
        except (ValueError, TypeError):
            return None
        if len(macos_parts) > 1:
            return macos_parts[1]
        return 5 + macos_parts[0]

    def get_macos_versions(self, minos=None, maxos=None, catalog=""):
        if minos is None:
            minos = self.min_macos
        if maxos is None:
            maxos = self.current_macos
        if minos > maxos:
            minos, maxos = maxos, minos
        os_versions = [
            self.num_to_macos(x, for_url=True) for x in range(minos, maxos + 1)
        ]
        if catalog:
            custom_cat_entry = os_versions[-1] + catalog
            os_versions.append(custom_cat_entry)
        return os_versions

    def build_url(self, **kwargs):
        catalog = kwargs.get("catalog", self.current_catalog).lower()
        catalog = catalog if catalog.lower() in self.catalog_suffix else "publicrelease"
        version = int(kwargs.get("version", self.current_macos))
        return "https://swscan.apple.com/content/catalogs/others/index-{}.merged-1.sucatalog".format(
            "-".join(
                reversed(
                    self.get_macos_versions(
                        self.min_macos,
                        version,
                        catalog=self.catalog_suffix.get(catalog, ""),
                    )
                )
            )
        )

    def get_catalog_data(self) -> bool:
        """Fetch and parse the macOS product catalog."""
        if self.cancel_event and self.cancel_event.is_set():
            raise CancelledError()

        url = self.build_url(catalog=self.current_catalog, version=self.current_macos)
        self._update_status(f"Downloading {self.current_catalog} catalog from:\n{url}")

        local_catalog = os.path.join(
            project_root, "gibMacOS", "Scripts", "sucatalog.plist"
        )

        if self.save_local:
            self._update_status(f"Checking for local catalog at:\n{local_catalog}")
            if os.path.exists(local_catalog) and not self.force_local:
                self._update_status(" - Found - loading...")
                try:
                    with open(local_catalog, "rb") as f:
                        self.catalog_data = plist.load(f)
                        assert isinstance(self.catalog_data, dict)
                    self._update_status("Catalog loaded from local file.")
                    return True
                except Exception as e:
                    self._update_status(
                        f" - Error loading local catalog: {e}. Downloading instead..."
                    )
            elif self.force_local:
                self._update_status(" - Forcing re-download of local catalog...")
            else:
                self._update_status(
                    " - Local catalog not found - downloading instead..."
                )

        try:
            b = self.downloader.get_bytes(url, False)
            if self.cancel_event and self.cancel_event.is_set():
                raise CancelledError()
            self.catalog_data = plist.loads(b)
            self._update_status("Catalog downloaded successfully.")
        except Exception as e:
            self._update_status(f"Error downloading catalog: {e}")
            return False

        if self.save_local or self.force_local:
            self._update_status(f" - Saving catalog to:\n - {local_catalog}")
            try:
                with open(local_catalog, "wb") as f:
                    plist.dump(self.catalog_data, f)
                self._update_status("Catalog saved locally.")
            except Exception as e:
                self._update_status(f" - Error saving catalog: {e}")
                return False
        return True

    def get_installers(self, plist_dict=None):
        if not plist_dict:
            plist_dict = self.catalog_data
        if not plist_dict:
            return []
        mac_prods = []
        for p in plist_dict.get("Products", {}):
            if self.cancel_event and self.cancel_event.is_set():
                raise CancelledError()
            if not self.find_recovery:
                val = (
                    plist_dict.get("Products", {})
                    .get(p, {})
                    .get("ExtendedMetaInfo", {})
                    .get("InstallAssistantPackageIdentifiers", {})
                )
                if val.get("OSInstall", {}) == "com.apple.mpkg.OSInstall" or val.get(
                    "SharedSupport", ""
                ).startswith("com.apple.pkg.InstallAssistant"):
                    mac_prods.append(p)
            else:
                if any(
                    x
                    for x in plist_dict.get("Products", {})
                    .get(p, {})
                    .get("Packages", [])
                    if x["URL"].endswith(self.recovery_suffixes)
                ):
                    mac_prods.append(p)
        return mac_prods

    def get_build_version(self, dist_dict):
        build = version = name = "Unknown"
        try:
            dist_url = dist_dict.get("English", dist_dict.get("en", ""))
            assert dist_url
            dist_file = self.downloader.get_string(dist_url, False)
            assert isinstance(dist_file, str)
        except Exception:
            dist_file = ""
        build_search = (
            "macOSProductBuildVersion"
            if "macOSProductBuildVersion" in dist_file
            else "BUILD"
        )
        vers_search = (
            "macOSProductVersion" if "macOSProductVersion" in dist_file else "VERSION"
        )
        try:
            build = (
                dist_file.split("<key>{}</key>".format(build_search))[1]
                .split("<string>")[1]
                .split("</string>")[0]
            )
        except (IndexError, ValueError):
            pass
        try:
            version = (
                dist_file.split("<key>{}</key>".format(vers_search))[1]
                .split("<string>")[1]
                .split("</string>")[0]
            )
        except (IndexError, ValueError):
            pass
        try:
            name_match = re.search(r"<title>(.+?)</title>", dist_file)
            if name_match:
                name = name_match.group(1)
        except Exception:
            pass
        try:
            device_ids_match = re.search(
                r"var supportedDeviceIDs\s*=\s*\[([^]]+)\];", dist_file
            )
            if device_ids_match:
                device_ids = list(
                    set(
                        i.lower()
                        for i in re.findall(r"'([^',]+)'", device_ids_match.group(1))
                    )
                )
            else:
                device_ids = []
        except Exception:
            device_ids = []
        return (build, version, name, device_ids)

    def get_dict_for_prods(
        self, prods: List[Any], plist_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """Return a list of product dictionaries for the given products."""
        self._update_status("Scanning products after catalog download...")
        plist_dict = plist_dict or self.catalog_data or {}
        prod_list = []
        prod_keys = (
            "build",
            "date",
            "description",
            "device_ids",
            "installer",
            "product",
            "time",
            "title",
            "version",
        )

        def get_packages_and_size(plist_dict, prod, recovery):
            packages = []
            if recovery:
                packages = [
                    x
                    for x in plist_dict.get("Products", {})
                    .get(prod, {})
                    .get("Packages", [])
                    if x["URL"].endswith(self.recovery_suffixes)
                ]
            else:
                packages = (
                    plist_dict.get("Products", {}).get(prod, {}).get("Packages", [])
                )
            size = self.downloader.get_size(sum([i["Size"] for i in packages]))
            return (packages, size)

        def prod_valid(prod, prod_list, prod_keys):
            if (
                not isinstance(prod_list, dict)
                or prod not in prod_list
                or not all(x in prod_list[prod] for x in prod_keys)
            ):
                return False
            if any(prod_list[prod].get(x, "Unknown") == "Unknown" for x in prod_keys):
                return False
            return True

        prod_changed = False
        for prod in prods:
            if self.cancel_event and self.cancel_event.is_set():
                raise CancelledError()
            if prod_valid(prod, self.prod_cache, prod_keys):
                prodd = {}
                for key in self.prod_cache[prod]:
                    prodd[key] = self.prod_cache[prod][key]
                prodd["packages"], prodd["size"] = get_packages_and_size(
                    plist_dict, prod, self.find_recovery
                )
                prod_list.append(prodd)
                continue

            prodd = {"product": prod}
            try:
                url = (
                    plist_dict.get("Products", {})
                    .get(prod, {})
                    .get("ServerMetadataURL", "")
                )
                assert url
                b = self.downloader.get_bytes(url, False)
                smd = plist.loads(b)
            except Exception:
                smd = {}

            prodd["date"] = (
                plist_dict.get("Products", {}).get(prod, {}).get("PostDate", "")
            )
            prodd["installer"] = (
                plist_dict.get("Products", {})
                .get(prod, {})
                .get("ExtendedMetaInfo", {})
                .get("InstallAssistantPackageIdentifiers", {})
                .get("OSInstall", {})
                == "com.apple.mpkg.OSInstall"
            )
            prodd["time"] = (
                time.mktime(prodd["date"].timetuple()) + prodd["date"].microsecond / 1e6
            )
            prodd["version"] = smd.get("CFBundleShortVersionString", "Unknown").strip()
            try:
                desc = (
                    smd.get("localization", {})
                    .get("English", {})
                    .get("description", "")
                    .decode("utf-8")
                )
                desctext = desc.split('"p1">')[1].split("</a>")[0]
            except Exception:
                desctext = ""
            prodd["description"] = desctext
            prodd["packages"], prodd["size"] = get_packages_and_size(
                plist_dict, prod, self.find_recovery
            )
            prodd["size"] = self.downloader.get_size(
                sum([i["Size"] for i in prodd["packages"]])
            )
            prodd["build"], v, n, prodd["device_ids"] = self.get_build_version(
                plist_dict.get("Products", {}).get(prod, {}).get("Distributions", {})
            )
            prodd["title"] = (
                smd.get("localization", {}).get("English", {}).get("title", n)
            )
            if v.lower() != "unknown":
                prodd["version"] = v
            prod_list.append(prodd)

            if smd or not plist_dict.get("Products", {}).get(prod, {}).get(
                "ServerMetadataURL", ""
            ):
                prod_changed = True
                temp_prod = {}
                for key in prodd:
                    if key in ("packages", "size"):
                        continue
                    if prodd[key] == "Unknown":
                        temp_prod = None
                        break
                    temp_prod[key] = prodd[key]
                if temp_prod:
                    self.prod_cache[prod] = temp_prod

        if prod_changed and self.prod_cache:
            try:
                self.save_prod_cache()
            except Exception:
                pass

        prod_list = sorted(prod_list, key=lambda x: x["time"], reverse=True)
        return prod_list

    def start_caffeinate(self):
        if (
            sys.platform.lower() == "darwin"
            and self.caffeinate_downloads
            and os.path.isfile("/usr/bin/caffeinate")
        ):
            self.term_caffeinate_proc()
            self.caffeinate_process = subprocess.Popen(
                ["/usr/bin/caffeinate"],
                stderr=getattr(subprocess, "DEVNULL", open(os.devnull, "w")),
                stdout=getattr(subprocess, "DEVNULL", open(os.devnull, "w")),
                stdin=getattr(subprocess, "DEVNULL", open(os.devnull, "w")),
            )
        return self.caffeinate_process

    def term_caffeinate_proc(self):
        if self.caffeinate_process is None:
            return True
        try:
            if self.caffeinate_process.poll() is None:
                start = time.time()
                while self.caffeinate_process.poll() is None:
                    if time.time() - start > 10:
                        self._update_status(
                            f"Timed out trying to terminate caffeinate process with PID {self.caffeinate_process.pid}!"
                        )
                        return False
                    self.caffeinate_process.terminate()
                    time.sleep(0.02)
        except Exception:
            pass
        return True

    def download_prod(self, prod: Dict, download_dir: str, dmg: bool = False) -> None:
        """Download the given product to the specified directory."""
        # Use the Installers subdirectory for full installers
        installers_dir = os.path.join(download_dir, "Installers")
        os.makedirs(installers_dir, exist_ok=True)
        
        name = (
            "{} - {} {} ({})".format(
                prod["product"], prod["version"], prod["title"], prod["build"]
            )
            .replace(":", "")
            .strip()
        )
        full_download_path = os.path.join(installers_dir, name)

        dl_list = []
        for x in prod["packages"]:
            if not x.get("URL", None):
                continue
            if dmg and not x.get("URL", "").lower().endswith(".dmg"):
                continue
            dl_list.append(x)

        if not len(dl_list):
            raise ProgramError("There were no files to download for this product.")

        if not os.path.isdir(full_download_path):
            os.makedirs(full_download_path)

        self.term_caffeinate_proc()

        failed_downloads = []
        for c, x in enumerate(dl_list, start=1):
            if self.cancel_event and self.cancel_event.is_set():
                raise CancelledError()

            url = x["URL"]
            file_name = os.path.basename(url)
            file_path = os.path.join(full_download_path, file_name)

            resume_bytes = 0
            if os.path.exists(file_path):
                resume_bytes = os.path.getsize(file_path)

            self._update_status(
                f"Downloading file {c} of {len(dl_list)}: {file_name} to {full_download_path}"
            )

            try:
                self.start_caffeinate()
                result = self.downloader.stream_to_file(
                    url,
                    file_path,
                    resume_bytes=resume_bytes,
                    allow_resume=True,
                    callback=self.progress_callback,
                    cancel_event=self.cancel_event,
                )
                if result is None:
                    if self.cancel_event and self.cancel_event.is_set():
                        raise CancelledError("Download cancelled by user.")
                    else:
                        # Provide more detailed error information
                        error_msg = f"Download failed for {file_name}"
                        if "SecUpd2021-003Catalina.RecoveryHDUpdate.pkg" in file_name:
                            error_msg += " (This is a known problematic recovery package. It may have been removed from Apple's servers or requires special access.)"
                        raise Exception(error_msg)
                self._update_status(f"Successfully downloaded: {file_name}")
            except Exception as e:
                self._update_status(f"Failed to download {file_name}: {e}")
                failed_downloads.append(file_name)

                # Provide additional debugging information for failed downloads
                if "SecUpd2021-003Catalina.RecoveryHDUpdate.pkg" in file_name:
                    self._update_status(
                        "Note: This recovery package may be deprecated or removed from Apple's servers."
                    )
                    self._update_status(
                        "Consider trying a different recovery package or full installer instead."
                    )
            finally:
                self.term_caffeinate_proc()

        if failed_downloads:
            error_message = f"{len(failed_downloads)} files failed to download: {', '.join(failed_downloads)}"

            # Add specific guidance for common failures
            if "SecUpd2021-003Catalina.RecoveryHDUpdate.pkg" in failed_downloads:
                error_message += "\n\nNote: The Catalina recovery package may be deprecated or removed from Apple's servers."
                error_message += "\nConsider downloading a full installer instead of recovery packages."
                error_message += (
                    "\nYou can uncheck 'Show Recovery Only' to see full installers."
                )

            raise ProgramError(
                error_message,
                title="Download Failed",
            )
