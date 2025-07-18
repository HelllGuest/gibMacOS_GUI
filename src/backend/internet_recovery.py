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
import random
import string
from http.client import HTTPResponse
from typing import cast
from urllib.parse import urlparse
from urllib.request import HTTPError, Request, urlopen

from .exceptions import ProgramError


class MacRecovery:
    """Handles macrecovery downloads from Apple's servers."""

    # Constants from macrecovery.py
    MLB_ZERO = "00000000000000000"
    TYPE_SID = 16
    TYPE_K = 64
    TYPE_FG = 64

    INFO_PRODUCT = "AP"
    INFO_IMAGE_LINK = "AU"
    INFO_IMAGE_HASH = "AH"
    INFO_IMAGE_SESS = "AT"
    INFO_SIGN_LINK = "CU"
    INFO_SIGN_HASH = "CH"
    INFO_SIGN_SESS = "CT"
    INFO_REQUIRED = [
        INFO_PRODUCT,
        INFO_IMAGE_LINK,
        INFO_IMAGE_HASH,
        INFO_IMAGE_SESS,
        INFO_SIGN_LINK,
        INFO_SIGN_HASH,
        INFO_SIGN_SESS,
    ]

    def __init__(self, update_callback=None, progress_callback=None, cancel_event=None):
        self.update_callback = update_callback
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event
        self.session = None

        # Load board mappings
        self.board_mappings = self._load_board_mappings()

    def _load_board_mappings(self):
        """Load board ID to macOS version mappings."""
        boards_path = os.path.join(os.path.dirname(__file__), "boards.json")
        if os.path.exists(boards_path):
            try:
                with open(boards_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                if self.update_callback:
                    self.update_callback(f"Warning: Could not load board mappings: {e}")
        return {}

    def _update_status(self, message):
        """Update status via callback."""
        if self.update_callback:
            self.update_callback(message)

    def _update_progress(self, current, total):
        """Update progress via callback."""
        if self.progress_callback:
            self.progress_callback(current, total, 0)

    def _run_query(self, url, headers, post=None, raw=False):
        """Execute HTTP query with error handling."""
        if post is not None:
            data = "\n".join(entry + "=" + post[entry] for entry in post).encode()
        else:
            data = None

        req = Request(url=url, headers=headers, data=data)
        try:
            response = urlopen(req)
            if raw:
                return response
            return dict(response.info()), response.read()
        except HTTPError as e:
            raise ProgramError(
                f"HTTP error {e.code} when connecting to {url}: {e.reason}"
            )
        except Exception as e:
            raise ProgramError(f"Network error when connecting to {url}: {str(e)}")

    def _generate_id(self, id_type, id_value=None):
        """Generate random ID of specified type."""
        return id_value or "".join(
            random.choices(string.hexdigits[:16].upper(), k=id_type)
        )

    def get_session(self):
        """Get session from Apple's recovery servers."""
        self._check_cancellation()
        self._update_status("Getting session from Apple's recovery servers...")

        headers = {
            "Host": "osrecovery.apple.com",
            "Connection": "close",
            "User-Agent": "InternetRecovery/1.0",
        }

        headers, _ = self._run_query("http://osrecovery.apple.com/", headers)

        for header in headers:
            if header.lower() == "set-cookie":
                cookies = headers[header].split("; ")
                for cookie in cookies:
                    if cookie.startswith("session="):
                        self.session = cookie
                        self._update_status("Session obtained successfully.")
                        return cookie

        raise ProgramError("No session found in server response")

    def get_image_info(
        self, board_id, mlb=MLB_ZERO, diag=False, os_type="default", cid=None
    ):
        """Get recovery image information from Apple's servers."""
        self._check_cancellation()
        if not self.session:
            self.get_session()

        self._update_status(f"Getting image info for board {board_id}...")

        headers = {
            "Host": "osrecovery.apple.com",
            "Connection": "close",
            "User-Agent": "InternetRecovery/1.0",
            "Cookie": self.session,
            "Content-Type": "text/plain",
        }

        post = {
            "cid": self._generate_id(self.TYPE_SID, cid),
            "sn": mlb,
            "bid": board_id,
            "k": self._generate_id(self.TYPE_K),
            "fg": self._generate_id(self.TYPE_FG),
        }

        if diag:
            url = "http://osrecovery.apple.com/InstallationPayload/Diagnostics"
        else:
            url = "http://osrecovery.apple.com/InstallationPayload/RecoveryImage"
            post["os"] = os_type

        headers, output = self._run_query(url, headers, post)

        output = output.decode("utf-8")
        info = {}
        for line in output.split("\n"):
            try:
                key, value = line.split(": ")
                info[key] = value
            except ValueError:
                continue

        # Verify all required keys are present
        missing_keys = [k for k in self.INFO_REQUIRED if k not in info]
        if missing_keys:
            raise ProgramError(
                f"Missing required keys in server response: {missing_keys}"
            )

        self._update_status("Image info obtained successfully.")
        return info

    def _check_cancellation(self):
        """Check if download has been cancelled."""
        if self.cancel_event and self.cancel_event.is_set():
            raise ProgramError("Download cancelled by user")

    def download_image(self, image_url, session, filename, directory=""):
        """Download recovery image with progress tracking."""
        self._update_status(f"Downloading recovery image: {filename}")

        purl = urlparse(image_url)
        headers = {
            "Host": purl.hostname,
            "Connection": "close",
            "User-Agent": "InternetRecovery/1.0",
            "Cookie": "=".join(["AssetToken", session]),
        }

        response = self._run_query(image_url, headers, raw=True)
        response = cast(HTTPResponse, response)

        # Get file size for progress tracking
        content_length = response.headers.get("Content-Length")
        total_size = int(content_length) if content_length else 0

        # Determine appropriate subdirectory based on filename
        if filename.startswith("diagnostics_"):
            subdir = "Diagnostics"
        else:
            subdir = "Recovery"
            
        # Create output subdirectory
        if directory:
            target_dir = os.path.join(directory, subdir)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
        else:
            filepath = filename

        downloaded = 0
        try:
            with open(filepath, "wb") as f:
                while True:
                    # Check for cancellation before reading each chunk
                    self._check_cancellation()

                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        self._update_progress(downloaded, total_size)
        except ProgramError as e:
            # If cancelled, clean up partial file
            if "cancelled" in str(e).lower():
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception:
                    pass  # Ignore cleanup errors
            raise

        self._update_status(f"Download completed: {filename}")
        return filepath

    def get_available_boards(self):
        """Get list of available board IDs with their macOS versions."""
        return self.board_mappings

    def get_board_version(self, board_id):
        """Get macOS version for a specific board ID."""
        return self.board_mappings.get(board_id, "Unknown")

    def download_recovery_image(
        self, board_id, mlb=MLB_ZERO, diag=False, os_type="default", output_dir=""
    ):
        """Complete workflow to download a recovery image."""
        try:
            # Get image information
            info = self.get_image_info(board_id, mlb, diag, os_type)

            # Download the image
            image_url = info[self.INFO_IMAGE_LINK]
            session = info[self.INFO_IMAGE_SESS]
            filename = f"recovery_{board_id}_{os_type}.dmg"

            if diag:
                filename = f"diagnostics_{board_id}.dmg"

            filepath = self.download_image(image_url, session, filename, output_dir)

            # Return file info
            return {
                "filepath": filepath,
                "filename": filename,
                "size": os.path.getsize(filepath),
                "hash": info.get(self.INFO_IMAGE_HASH, ""),
                "product": info.get(self.INFO_PRODUCT, ""),
                "board_id": board_id,
                "mlb": mlb,
                "os_type": os_type,
                "is_diagnostics": diag,
            }

        except Exception as e:
            raise ProgramError(f"Failed to download recovery image: {str(e)}")
