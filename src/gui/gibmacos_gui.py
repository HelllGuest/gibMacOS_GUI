"""
gibMacOS GUI
https://github.com/HelllGuest/gibMacOS_GUI

Original gibMacOS by corpnewt: https://github.com/corpnewt/gibMacOS
macrecovery.py by acidanthera team: https://github.com/acidanthera/OpenCorePkg

GUI Author: Anoop Kumar
License: MIT
"""

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

from src.backend import CancelledError, GibMacOSBackend, ProgramError
from src.gui.dialogs import AboutDialog, HowToUseDialog
from src.gui.internet_recovery_dialog import MacRecoveryDialog
from src.utils.helpers import get_time_string, open_directory


class GibMacOSGUI(tk.Tk):
    """Main GUI application for gibMacOS."""

    def __init__(self) -> None:
        """Initialize the main GUI window and all components."""
        super().__init__()

        # Window configuration
        self.title("gibMacOS GUI")
        self.geometry("950x700")
        self.minsize(850, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Threading and queue management
        self.download_queue: queue.Queue = queue.Queue()
        self.after_id: Optional[str] = None
        self.cancel_event: threading.Event = threading.Event()
        self.current_thread: Optional[threading.Thread] = None

        # Download directory setup - cross-platform friendly approach
        import os
        
        # Use platform-specific documents directory
        if os.name == 'nt':  # Windows
            documents_dir = Path(os.path.expandvars("%USERPROFILE%\\Documents"))
        else:  # macOS and Linux
            documents_dir = Path.home() / "Documents"
        
        # Create a standardized directory structure
        self.download_dir: str = str(documents_dir / "gibMacOS-Downloads")
        
        # Create main download directory
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        
        # Create organized subdirectories for different types of downloads
        Path(self.download_dir, "Installers").mkdir(exist_ok=True)
        Path(self.download_dir, "Recovery").mkdir(exist_ok=True)
        Path(self.download_dir, "Diagnostics").mkdir(exist_ok=True)

        # Initialize backend
        self.backend = GibMacOSBackend(
            update_callback=self._queue_status_update,
            progress_callback=self._queue_progress_update,
            cancel_event=self.cancel_event,
        )

        # Initialize GUI variables
        self._init_gui_variables()

        # Data storage
        self.gui_products_data: list[dict] = []

        # Create GUI components
        self._create_widgets()

        # Start queue processing and refresh products
        self._check_queue()
        self._refresh_products()

    def _init_gui_variables(self):
        """Initialize GUI variables."""
        self.current_catalog_var = tk.StringVar(
            self, value=self.backend.current_catalog
        )
        self.max_macos_var = tk.StringVar(
            self,
            value=self.backend.num_to_macos(self.backend.current_macos, for_url=False),
        )
        self.find_recovery_var = tk.BooleanVar(self, value=self.backend.find_recovery)
        self.caffeinate_downloads_var = tk.BooleanVar(
            self, value=self.backend.caffeinate_downloads
        )
        self.download_dir_var = tk.StringVar(self, value=self.download_dir)
        self.save_local_var = tk.BooleanVar(self, value=self.backend.save_local)
        self.force_local_var = tk.BooleanVar(self, value=self.backend.force_local)
        self.show_console_log_var = tk.BooleanVar(self, value=True)

        # Sorting variables
        self.sort_column = tk.StringVar(value="Name")
        self.sort_reverse = tk.BooleanVar(value=False)

        # Store the current product data for sorting
        self.current_product_data = []

    def _on_close(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.current_thread and self.current_thread.is_alive():
            self.cancel_event.set()
            self.current_thread.join(timeout=2.0)
        self.destroy()

    def _queue_status_update(self, message: str) -> None:
        """Queue a status update message."""
        logging.debug(f"Status update: {message}")
        self.download_queue.put(("status", message))

    def _queue_progress_update(
        self, current_bytes: int, total_bytes: int, start_time: float
    ) -> None:
        """Queue a progress update."""
        self.download_queue.put(("progress", (current_bytes, total_bytes, start_time)))

    def _queue_error_dialog(self, title: str, message: str) -> None:
        """Queue an error dialog."""
        logging.error(f"Error dialog: {title} - {message}")
        self.download_queue.put(("error", (title, message)))

    def _queue_info_dialog(self, title: str, message: str) -> None:
        """Queue an info dialog."""
        logging.info(f"Info dialog: {title} - {message}")
        self.download_queue.put(("info", (title, message)))

    def _queue_ui_state(self, enabled: bool) -> None:
        """Queue UI state change."""
        self.download_queue.put(("ui_state", enabled))

    def _check_queue(self) -> None:
        """Process queued messages from background threads."""
        try:
            while True:
                try:
                    msg_type, data = self.download_queue.get_nowait()

                    if msg_type == "status":
                        self.status_label.config(text=data)
                        self._write_to_console(f"STATUS: {data}")
                    elif msg_type == "progress":
                        current, total, start_time = data
                        self._update_progress_bar(current, total, start_time)
                    elif msg_type == "error":
                        messagebox.showerror(data[0], data[1])
                        self._write_to_console(f"ERROR: {data[0]} - {data[1]}")
                    elif msg_type == "info":
                        messagebox.showinfo(data[0], data[1])
                        self._write_to_console(f"INFO: {data[0]} - {data[1]}")
                    elif msg_type == "ui_state":
                        self._set_ui_state(data)
                    elif msg_type == "populate_products":
                        self._populate_product_tree(data)

                    self.download_queue.task_done()
                except queue.Empty:
                    break
        except Exception as e:
            logging.exception(f"Error processing queue: {e}")
        finally:
            self.after_id = str(self.after(100, self._check_queue))

    def _update_status_label(self, message):
        """Update the status label with a message."""
        self.status_label.config(text=message)

    def _update_progress_bar(self, current, total, start_time):
        """Update the progress bar with current download progress."""
        if total > 0:
            percent = (current / total) * 100
            self.progress_bar["value"] = percent

            elapsed_time = time.time() - start_time
            if elapsed_time > 0 and current > 0:
                speed = current / elapsed_time
                time_remaining = (total - current) / speed if speed > 0 else 0
                speed_str = self.backend.downloader.get_size(speed).replace("B", "B/s")
                eta_str = get_time_string(time_remaining)
                self.progress_bar_label.config(
                    text=f"{percent:.2f}% ({self.backend.downloader.get_size(current)} / {self.backend.downloader.get_size(total)}) - {speed_str} - ETA {eta_str}"
                )
            else:
                self.progress_bar_label.config(
                    text=f"{percent:.2f}% ({self.backend.downloader.get_size(current)} / {self.backend.downloader.get_size(total)})"
                )
        else:
            self.progress_bar["value"] = 0
            self.progress_bar_label.config(text="")

    def _write_to_console(self, message):
        """Write a message to the console log."""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, message + "\n")
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)

    def _create_widgets(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(
            label="Open Download Directory", command=self._open_download_dir
        )
        self.file_menu.add_command(
            label="macrecovery", command=self._show_internet_recovery
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_close)

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="How to Use", command=self._show_how_to_use)
        self.help_menu.add_command(label="About", command=self._show_about)

        # Main container frame
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Settings frame
        self.settings_frame = ttk.LabelFrame(
            self.main_container, text="Settings", padding="10"
        )
        self.settings_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Products frame
        self.products_frame = ttk.LabelFrame(
            self.main_container, text="Available items", padding="10"
        )
        self.products_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bottom panel frame
        self.bottom_panel_frame = ttk.Frame(self.main_container)
        self.bottom_panel_frame.pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=5
        )
        self.bottom_panel_frame.grid_rowconfigure(0, weight=0)
        self.bottom_panel_frame.grid_rowconfigure(1, weight=1)
        self.bottom_panel_frame.grid_columnconfigure(0, weight=1)

        # Status frame
        self.status_frame = ttk.LabelFrame(
            self.bottom_panel_frame, text="Status", padding="10"
        )
        self.status_frame.grid(row=0, column=0, sticky=tk.NSEW)

        # Console log frame
        self.console_log_frame = ttk.LabelFrame(
            self.bottom_panel_frame, text="Console Log", padding="10"
        )
        self.console_text = scrolledtext.ScrolledText(
            self.console_log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        if self.show_console_log_var.get():
            self.console_log_frame.grid(row=1, column=0, sticky=tk.NSEW)

        # Catalog selection
        ttk.Label(self.settings_frame, text="Catalog:").grid(
            row=0, column=0, padx=5, pady=2, sticky=tk.W
        )
        self.catalog_dropdown = ttk.OptionMenu(
            self.settings_frame,
            self.current_catalog_var,
            self.current_catalog_var.get(),
            *list(self.backend.catalog_suffix.keys()),
            command=self._on_catalog_change,
        )
        self.catalog_dropdown.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        # Max macOS version
        ttk.Label(self.settings_frame, text="Max macOS Version:").grid(
            row=1, column=0, padx=5, pady=2, sticky=tk.W
        )
        self.max_macos_entry = ttk.Entry(
            self.settings_frame, textvariable=self.max_macos_var, width=10
        )
        self.max_macos_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        self.max_macos_entry.bind("<Return>", self._on_max_macos_change)

        # Checkboxes frame
        self.checkboxes_frame = ttk.Frame(self.settings_frame)
        self.checkboxes_frame.grid(
            row=0, column=2, rowspan=2, padx=10, pady=2, sticky=tk.W
        )

        self.find_recovery_checkbox = ttk.Checkbutton(
            self.checkboxes_frame,
            text="Show Recovery Only",
            variable=self.find_recovery_var,
            command=self._on_find_recovery_toggle,
        )
        self.find_recovery_checkbox.grid(row=0, column=0, padx=5, sticky=tk.W)

        self.caffeinate_checkbox = ttk.Checkbutton(
            self.checkboxes_frame,
            text="Caffeinate Downloads (macOS only)",
            variable=self.caffeinate_downloads_var,
            command=self._on_caffeinate_toggle,
        )
        self.caffeinate_checkbox.grid(row=1, column=0, padx=5, sticky=tk.W)
        if sys.platform != "darwin":
            self.caffeinate_checkbox.config(state=tk.DISABLED)

        self.save_local_checkbox = ttk.Checkbutton(
            self.checkboxes_frame,
            text="Save Catalog Locally",
            variable=self.save_local_var,
            command=self._on_save_local_toggle,
        )
        self.save_local_checkbox.grid(row=0, column=1, padx=5, sticky=tk.W)

        self.force_local_checkbox = ttk.Checkbutton(
            self.checkboxes_frame,
            text="Force Local Catalog Re-download",
            variable=self.force_local_var,
            command=self._on_force_local_toggle,
        )
        self.force_local_checkbox.grid(row=1, column=1, padx=5, sticky=tk.W)

        self.show_console_checkbox = ttk.Checkbutton(
            self.checkboxes_frame,
            text="Show Console Log",
            variable=self.show_console_log_var,
            command=self._toggle_console_log,
        )
        self.show_console_checkbox.grid(row=0, column=2, padx=5, sticky=tk.W)

        # Download directory
        ttk.Label(self.settings_frame, text="Download Directory:").grid(
            row=2, column=0, padx=5, pady=2, sticky=tk.W
        )
        self.download_dir_entry = ttk.Entry(
            self.settings_frame,
            textvariable=self.download_dir_var,
            width=50,
            state=tk.DISABLED,
        )
        self.download_dir_entry.grid(
            row=2, column=1, columnspan=2, padx=5, pady=2, sticky="ew"
        )
        self.browse_dir_button = ttk.Button(
            self.settings_frame, text="Browse", command=self._browse_download_dir
        )
        self.browse_dir_button.grid(row=2, column=3, padx=5, pady=2, sticky=tk.W)

        # Buttons frame
        self.buttons_frame = ttk.Frame(self.settings_frame)
        self.buttons_frame.grid(row=3, column=0, columnspan=4, pady=5, sticky=tk.W)

        # Rearranged buttons for logical grouping
        self.refresh_button = ttk.Button(
            self.buttons_frame, text="Refresh Products", command=self._refresh_products
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.download_button = ttk.Button(
            self.buttons_frame,
            text="Download Selected",
            command=self._download_selected,
            state=tk.DISABLED,
        )
        self.download_button.pack(side=tk.LEFT, padx=5)

        self.internet_recovery_button = ttk.Button(
            self.buttons_frame,
            text="macrecovery",
            command=self._show_internet_recovery,
            state=tk.DISABLED,
        )
        self.internet_recovery_button.pack(side=tk.LEFT, padx=5)

        self.set_su_button = ttk.Button(
            self.buttons_frame,
            text="Set SU CatalogURL",
            command=self._set_su_catalog,
            state=tk.NORMAL if sys.platform == "darwin" else tk.DISABLED,
        )
        self.set_su_button.pack(side=tk.LEFT, padx=5)

        self.clear_su_button = ttk.Button(
            self.buttons_frame,
            text="Clear SU CatalogURL",
            command=self._clear_su_catalog,
            state=tk.NORMAL if sys.platform == "darwin" else tk.DISABLED,
        )
        self.clear_su_button.pack(side=tk.LEFT, padx=5)

        # Cancel button
        self.cancel_button = ttk.Button(
            self.buttons_frame,
            text="Cancel",
            command=self._cancel_operation,
            state=tk.DISABLED,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # Exit button (moved to the end)
        self.exit_button = ttk.Button(
            self.buttons_frame, text="Exit", command=self._on_close
        )
        self.exit_button.pack(side=tk.LEFT, padx=5)

        # Products treeview
        self.product_tree = ttk.Treeview(
            self.products_frame,
            columns=("Name", "Version", "Build", "Size", "Product ID"),
            show="headings",
        )
        self.product_tree.heading(
            "Name",
            text="macOS Name",
            anchor=tk.W,
            command=lambda: self._sort_treeview("Name"),
        )
        self.product_tree.heading(
            "Version",
            text="Version",
            anchor=tk.W,
            command=lambda: self._sort_treeview("Version"),
        )
        self.product_tree.heading(
            "Build",
            text="Build",
            anchor=tk.W,
            command=lambda: self._sort_treeview("Build"),
        )
        self.product_tree.heading(
            "Size",
            text="Size",
            anchor=tk.E,
            command=lambda: self._sort_treeview("Size"),
        )
        self.product_tree.heading(
            "Product ID",
            text="Product ID",
            anchor=tk.W,
            command=lambda: self._sort_treeview("Product ID"),
        )

        self.product_tree.column("Name", width=300, stretch=tk.YES)
        self.product_tree.column("Version", width=100, stretch=tk.NO)
        self.product_tree.column("Build", width=100, stretch=tk.NO)
        self.product_tree.column("Size", width=80, anchor=tk.E, stretch=tk.NO)
        self.product_tree.column("Product ID", width=100, stretch=tk.NO)

        scrollbar = ttk.Scrollbar(
            self.products_frame, orient="vertical", command=self.product_tree.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        self.product_tree.pack(fill=tk.BOTH, expand=True)

        self.product_tree.bind("<<TreeviewSelect>>", self._on_product_select)

        # Status bar
        self.status_label = ttk.Label(self.status_frame, text="Ready.", wraplength=750)
        self.status_label.pack(fill=tk.X, pady=2)

        self.progress_bar = ttk.Progressbar(
            self.status_frame, orient="horizontal", length=200, mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, pady=2)
        self.progress_bar_label = ttk.Label(self.status_frame, text="")
        self.progress_bar_label.pack(pady=2)

    def _on_catalog_change(self, selected_catalog):
        self.backend.current_catalog = (
            selected_catalog.lower()
            if selected_catalog.lower() in self.backend.catalog_suffix
            else "publicrelease"
        )
        self.backend.save_settings()
        self._refresh_products()

    def _on_max_macos_change(self, event=None):
        version_str = self.max_macos_var.get().strip()
        version_num = self.backend.macos_to_num(version_str)
        if version_num:
            self.backend.current_macos = version_num
            self.backend.save_settings()
            self._refresh_products()
        else:
            self._queue_error_dialog(
                "Invalid Input",
                "Please enter a valid macOS version (e.g., 10.15, 11, 12).",
            )
            self.max_macos_var.set(
                self.backend.num_to_macos(self.backend.current_macos, for_url=False)
            )

    def _on_find_recovery_toggle(self):
        self.backend.find_recovery = self.find_recovery_var.get()
        self.backend.save_settings()
        self._refresh_products()

    def _on_caffeinate_toggle(self):
        self.backend.caffeinate_downloads = self.caffeinate_downloads_var.get()
        self.backend.save_settings()

    def _on_save_local_toggle(self):
        self.backend.save_local = self.save_local_var.get()
        self.backend.save_settings()

    def _on_force_local_toggle(self):
        self.backend.force_local = self.force_local_var.get()
        self.backend.save_settings()

    def _toggle_console_log(self):
        if self.show_console_log_var.get():
            self.console_log_frame.grid(row=1, column=0, sticky=tk.NSEW)
        else:
            self.console_log_frame.grid_forget()

    def _browse_download_dir(self):
        selected_dir = filedialog.askdirectory(initialdir=self.download_dir)
        if selected_dir:
            self.download_dir = selected_dir
            self.download_dir_var.set(selected_dir)

    def _open_download_dir(self):
        """Open the download directory in Finder (macOS) or File Explorer (Windows/Linux)."""
        try:
            download_dir = self.download_dir_var.get()
            open_directory(download_dir)
            self._queue_status_update(f"Opened download directory: {download_dir}")
        except Exception as e:
            self._queue_error_dialog(
                "Error Opening Directory",
                f"Could not open download directory:\n{str(e)}",
            )

    def _set_su_catalog(self):
        if sys.platform != "darwin":
            self._queue_info_dialog(
                "Not Applicable", "This feature is only available on macOS."
            )
            return

        self._set_ui_state(False)
        self.cancel_event.clear()

        def run_command():
            try:
                self._queue_status_update("Setting Software Update Catalog URL...")
                url = self.backend.build_url()
                self.backend.runner.run(
                    {"args": ["softwareupdate", "--set-catalog", url], "sudo": True}
                )
                self._queue_status_update(f"Software Update Catalog URL set to:\n{url}")
            except Exception as e:
                self._queue_status_update(
                    f"Failed to set Software Update Catalog URL: {e}"
                )
                self._queue_error_dialog(
                    "Error",
                    f"Failed to set Software Update Catalog URL: {e}\n(Might require administrator privileges.)",
                )
            finally:
                self._queue_ui_state(True)
                self.current_thread = None

        self.current_thread = threading.Thread(target=run_command)
        self.current_thread.start()

    def _clear_su_catalog(self):
        if sys.platform != "darwin":
            self._queue_info_dialog(
                "Not Applicable", "This feature is only available on macOS."
            )
            return

        self._set_ui_state(False)
        self.cancel_event.clear()

        def run_command():
            try:
                self._queue_status_update("Clearing Software Update Catalog URL...")
                self.backend.runner.run(
                    {"args": ["softwareupdate", "--clear-catalog"], "sudo": True}
                )
                self._queue_status_update("Software Update Catalog URL cleared.")
            except Exception as e:
                self._queue_status_update(
                    f"Failed to clear Software Update Catalog URL: {e}"
                )
                self._queue_error_dialog(
                    "Error",
                    f"Failed to clear Software Update Catalog URL: {e}\n(Might require administrator privileges.)",
                )
            finally:
                self._queue_ui_state(True)
                self.current_thread = None

        self.current_thread = threading.Thread(target=run_command)
        self.current_thread.start()

    def _refresh_products(self):
        self._set_ui_state(False)
        self.cancel_event.clear()

        self._queue_status_update(
            "Fetching and parsing macOS product catalog, please wait..."
        )
        self.progress_bar["value"] = 0
        self.progress_bar_label.config(text="")
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(100)

        def fetch_products_task():
            try:
                if self.backend.force_local:
                    self.backend.prod_cache = {}

                if not self.backend.get_catalog_data():
                    if self.cancel_event.is_set():
                        raise CancelledError("Catalog download cancelled.")
                    else:
                        raise ProgramError(
                            "Failed to retrieve catalog data. Check internet connection or catalog settings."
                        )

                mac_prods_data = self.backend.get_dict_for_prods(
                    self.backend.get_installers()
                )

                if self.cancel_event.is_set():
                    raise CancelledError("Product scanning cancelled.")

                self.download_queue.put(("populate_products", mac_prods_data))
                self._queue_status_update("Catalog refreshed. Populating products...")
            except CancelledError as e:
                self._queue_status_update(str(e))
                self._queue_info_dialog(e.title, str(e))
            except ProgramError as e:
                self._queue_status_update(f"Error refreshing products: {e.title} - {e}")
                self._queue_error_dialog(e.title, str(e))
            except Exception as e:
                self._queue_status_update(f"An unexpected error occurred: {e}")
                self._queue_error_dialog("Error", str(e))
            finally:
                self.progress_bar.stop()
                self.progress_bar.config(mode="determinate")
                self.progress_bar["value"] = 0
                self.progress_bar_label.config(text="")
                self._queue_status_update("Ready.")
                self._queue_ui_state(True)
                self.current_thread = None

        self.current_thread = threading.Thread(target=fetch_products_task)
        self.current_thread.start()

    def _populate_product_tree(self, mac_prods_data):
        self.product_tree.delete(*self.product_tree.get_children())
        self.gui_products_data = mac_prods_data
        # Store data for sorting
        self.current_product_data = []
        for p in mac_prods_data:
            display_name = f"{p['title']} {p['version']}"
            if p["build"].lower() != "unknown":
                display_name += f" ({p['build']})"
            item_data = (
                display_name,
                p["version"],
                p["build"],
                p["size"],
                p["product"],
            )
            self.current_product_data.append(item_data)
            self.product_tree.insert(
                "",
                tk.END,
                iid=str(p["product"]),
                values=item_data,
            )
        self._queue_status_update(f"Found {len(mac_prods_data)} items")
        # Clear selection after repopulating to avoid stale selection
        self.product_tree.selection_remove(self.product_tree.selection())
        self.download_button.config(state=tk.DISABLED)

    def _on_product_select(self, event):
        selected_items = self.product_tree.selection()
        valid_ids = [str(p["product"]) for p in self.gui_products_data]
        if selected_items and selected_items[0] in valid_ids:
            self.download_button.config(state=tk.NORMAL)
        else:
            self.download_button.config(state=tk.DISABLED)

    def _download_selected(self):
        selected_items = self.product_tree.selection()
        if not selected_items:
            self._queue_info_dialog(
                "No Selection", "Please select a macOS product to download."
            )
            return
        selected_item_id = selected_items[0]
        valid_ids = [str(p["product"]) for p in self.gui_products_data]
        if selected_item_id not in valid_ids:
            self._queue_error_dialog(
                "Error",
                "Invalid selection. Please select a valid macOS product from the list.",
            )
            return
        selected_prod = next(
            (
                p
                for p in self.gui_products_data
                if str(p["product"]) == str(selected_item_id)
            ),
            None,
        )
        if not selected_prod:
            self._queue_error_dialog(
                "Error",
                "Selected product not found in displayed data. Please refresh products.",
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Download",
            f"Are you sure you want to download '{selected_prod['title']} {selected_prod['version']} ({selected_prod['build']})' "
            f"to '{self.download_dir}'?",
        )
        if not confirm:
            return

        self._set_ui_state(False)
        self.cancel_event.clear()
        self.progress_bar["value"] = 0
        self.progress_bar_label.config(text="Starting download...")
        self._queue_status_update(
            f"Initiating download for {selected_prod['title']}..."
        )

        def download_task():
            try:
                self.backend.download_prod(selected_prod, self.download_dir)
                self._queue_status_update(
                    f"Download complete for {selected_prod['title']}!"
                )
                self._queue_info_dialog(
                    "Download Complete",
                    f"All files for {selected_prod['title']} downloaded successfully to:\n"
                    f"{os.path.join(self.download_dir, selected_prod['product'])}",
                )
            except CancelledError as e:
                self._queue_status_update(str(e))
                self._queue_info_dialog(e.title, str(e))
            except ProgramError as e:
                self._queue_status_update(f"Download error: {e.title} - {e}")
                self._queue_error_dialog(e.title, str(e))
            except Exception as e:
                self._queue_status_update(
                    f"An unexpected error occurred during download: {e}"
                )
                self._queue_error_dialog("Error", str(e))
            finally:
                self._queue_progress_update(0, 0, 0)
                self._queue_ui_state(True)
                self._queue_status_update("Ready.")
                self.current_thread = None

        self.current_thread = threading.Thread(target=download_task)
        self.current_thread.start()

    def _cancel_operation(self):
        if messagebox.askyesno(
            "Confirm Cancel", "Are you sure you want to cancel the current operation?"
        ):
            self.cancel_event.set()
            self._queue_status_update("Cancelling current operation, please wait...")

    def _set_ui_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.catalog_dropdown.config(state=state)
        self.max_macos_entry.config(state=state)
        self.find_recovery_checkbox.config(state=state)
        self.caffeinate_checkbox.config(
            state=state if sys.platform == "darwin" else tk.DISABLED
        )
        self.save_local_checkbox.config(state=state)
        self.force_local_checkbox.config(state=state)
        self.browse_dir_button.config(state=state)

        set_su_state = (
            tk.NORMAL if enabled and sys.platform == "darwin" else tk.DISABLED
        )
        clear_su_state = (
            tk.NORMAL if enabled and sys.platform == "darwin" else tk.DISABLED
        )

        self.set_su_button.config(state=set_su_state)
        self.clear_su_button.config(state=clear_su_state)

        self.product_tree.config(selectmode="extended" if enabled else "none")

        if enabled and self.product_tree.selection():
            self.download_button.config(state=tk.NORMAL)
        else:
            self.download_button.config(state=tk.DISABLED)

        # Enable macrecovery button when UI is enabled
        self.internet_recovery_button.config(state=state)

        self.cancel_button.config(state=tk.NORMAL if not enabled else tk.DISABLED)
        self.show_console_checkbox.config(state=tk.NORMAL)

    def _show_how_to_use(self):
        """Show the how to use dialog."""
        dialog = HowToUseDialog(self)
        dialog.show()

    def _show_about(self):
        """Show the about dialog."""
        dialog = AboutDialog(self)
        dialog.show()

    def _show_internet_recovery(self):
        """Show the Internet Recovery dialog."""
        dialog = MacRecoveryDialog(self)
        dialog.show()

    def _sort_treeview(self, column):
        """Sort the treeview based on the selected column."""
        if not self.current_product_data:
            return

        # Toggle sort direction if same column, otherwise set to ascending
        if self.sort_column.get() == column:
            self.sort_reverse.set(not self.sort_reverse.get())
        else:
            self.sort_column.set(column)
            self.sort_reverse.set(False)

        # Sort the data
        reverse = self.sort_reverse.get()

        # Define sort key functions for different columns
        def get_sort_key(item):
            if column == "Name":
                return item[0].lower()  # Name column
            elif column == "Version":
                # Extract version numbers for proper sorting
                version = item[1]
                try:
                    # Split version into parts and convert to numbers for proper sorting
                    parts = version.split(".")
                    return [int(part) if part.isdigit() else part for part in parts]
                except (ValueError, TypeError):
                    return version.lower()
            elif column == "Build":
                return item[2].lower()  # Build column
            elif column == "Size":
                # Convert size string to bytes for proper sorting
                size_str = item[3]
                try:
                    # Extract number and unit
                    import re

                    match = re.match(r"(\d+(?:\.\d+)?)\s*([KMGT]?B)", size_str)
                    if match:
                        number, unit = match.groups()
                        number = float(number)
                        multipliers = {
                            "B": 1,
                            "KB": 1024,
                            "MB": 1024**2,
                            "GB": 1024**3,
                            "TB": 1024**4,
                        }
                        return number * multipliers.get(unit, 1)
                    return 0
                except (ValueError, TypeError):
                    return size_str.lower()
            elif column == "Product ID":
                return item[4].lower()  # Product ID column
            else:
                return item[0].lower()  # Default to name

        # Sort the data
        sorted_data = sorted(
            self.current_product_data, key=get_sort_key, reverse=reverse
        )

        # Clear and repopulate the treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        for item_data in sorted_data:
            self.product_tree.insert("", "end", values=item_data)

        # Update column header to show sort direction
        base_headers = {
            "Name": "macOS Name",
            "Version": "Version",
            "Build": "Build",
            "Size": "Size",
            "Product ID": "Product ID",
        }

        for col in ("Name", "Version", "Build", "Size", "Product ID"):
            if col == column:
                direction = " ▼" if reverse else " ▲"
                self.product_tree.heading(col, text=f"{base_headers[col]}{direction}")
            else:
                # Remove sort indicators from other columns
                self.product_tree.heading(col, text=base_headers[col])

    def _scan_products(self):
        # Show progress to user during long scan
        self._queue_status_update(
            "Scanning products... (this may take a while, please wait)"
        )
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(100)  # 100ms interval for smooth animation
        self.update_idletasks()
        try:
            # ... existing scanning logic ...
            pass
        finally:
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.progress_bar["value"] = 0
            self.progress_bar_label.config(text="")


if __name__ == "__main__":
    print(f"\nLaunching gibMacOS GUI from {__file__}...")
    gui = GibMacOSGUI()
    gui.mainloop()
