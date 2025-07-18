"""
macrecovery Dialog for gibMacOSGUI.

Provides a user interface for downloading recovery images directly from Apple's servers
using macrecovery functionality.
"""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.backend import MacRecovery
from src.utils.helpers import center_window


class MacRecoveryDialog:
    """Dialog for macrecovery downloads."""

    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.macrecovery = None
        self.available_boards = {}
        self.download_thread = None
        self.cancel_event = threading.Event()

    def show(self):
        """Show the macrecovery dialog."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("macrecovery")
        self.window.geometry("700x450")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Initialize macrecovery
        self.macrecovery = MacRecovery(
            update_callback=self._update_status,
            progress_callback=self._update_progress,
            cancel_event=self.cancel_event,
        )

        # Load available boards
        self.available_boards = self.macrecovery.get_available_boards()

        self._create_widgets()
        self._populate_boards()

        # Center window
        center_window(self.parent, self.window)

    def _create_widgets(self):
        """Create the dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=False)

        # Board selection frame
        board_frame = ttk.LabelFrame(main_frame, text="Board Selection", padding=10)
        board_frame.pack(fill=tk.X, pady=(0, 10))

        # Board ID entry
        ttk.Label(board_frame, text="Board ID:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        self.board_id_var = tk.StringVar()
        self.board_id_entry = ttk.Entry(
            board_frame, textvariable=self.board_id_var, width=30
        )
        self.board_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Board version display
        ttk.Label(board_frame, text="macOS Version:").grid(
            row=0, column=2, padx=5, pady=5, sticky=tk.W
        )
        self.version_label = ttk.Label(board_frame, text="Unknown")
        self.version_label.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # Board selection dropdown
        ttk.Label(board_frame, text="Or select from list:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W
        )
        self.board_dropdown = ttk.Combobox(board_frame, width=40, state="readonly")
        self.board_dropdown.grid(
            row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W
        )
        self.board_dropdown.bind("<<ComboboxSelected>>", self._on_board_selected)

        # MLB entry
        ttk.Label(board_frame, text="MLB Serial:").grid(
            row=2, column=0, padx=5, pady=5, sticky=tk.W
        )
        self.mlb_var = tk.StringVar(value="00000000000000000")
        self.mlb_entry = ttk.Entry(board_frame, textvariable=self.mlb_var, width=30)
        self.mlb_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Download Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # OS type selection
        ttk.Label(options_frame, text="OS Type:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        self.os_type_var = tk.StringVar(value="default")
        os_type_combo = ttk.Combobox(
            options_frame,
            textvariable=self.os_type_var,
            values=["default", "latest"],
            state="readonly",
            width=15,
        )
        os_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Diagnostics checkbox
        self.diagnostics_var = tk.BooleanVar(value=False)
        diagnostics_check = ttk.Checkbutton(
            options_frame, text="Download Diagnostics", variable=self.diagnostics_var
        )
        diagnostics_check.grid(row=0, column=2, padx=20, pady=5, sticky=tk.W)

        # Output directory
        ttk.Label(options_frame, text="Output Directory:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W
        )
        
        # Use the same cross-platform directory as the main app
        if os.name == 'nt':  # Windows
            documents_dir = os.path.join(os.path.expandvars("%USERPROFILE%"), "Documents")
        else:  # macOS and Linux
            documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
            
        default_dir = os.path.join(documents_dir, "gibMacOS-Downloads")
        self.output_dir_var = tk.StringVar(value=default_dir)
        output_dir_entry = ttk.Entry(
            options_frame, textvariable=self.output_dir_var, width=40
        )
        output_dir_entry.grid(
            row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W
        )

        browse_button = ttk.Button(
            options_frame, text="Browse", command=self._browse_output_dir
        )
        browse_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = ttk.Label(
            status_frame, text="Ready to download.", wraplength=650
        )
        self.status_label.pack(fill=tk.X, pady=2)

        self.progress_bar = ttk.Progressbar(
            status_frame, orient="horizontal", mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, pady=2)

        self.progress_label = ttk.Label(status_frame, text="")
        self.progress_label.pack(pady=2)

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 0), expand=False, anchor="n")

        self.download_button = ttk.Button(
            buttons_frame, text="Download", command=self._start_download
        )
        self.download_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel_download,
            state=tk.DISABLED,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(buttons_frame, text="Close", command=self._close_window).pack(
            side=tk.RIGHT, padx=5
        )

    def _populate_boards(self):
        """Populate the board dropdown with available boards."""
        board_list = []
        for board_id, version in self.available_boards.items():
            board_list.append(f"{board_id} ({version})")

        self.board_dropdown["values"] = sorted(board_list)

    def _on_board_selected(self, event):
        """Handle board selection from dropdown."""
        selection = self.board_dropdown.get()
        if selection:
            board_id = selection.split(" (")[0]
            self.board_id_var.set(board_id)
            version = self.available_boards.get(board_id, "Unknown")
            self.version_label.config(text=version)

    def _browse_output_dir(self):
        """Browse for output directory."""
        from tkinter import filedialog

        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)

    def _update_status(self, message):
        """Update status label."""
        if self.window:
            self.status_label.config(text=message)
            self.window.update_idletasks()

    def _update_progress(self, current, total, start_time):
        """Update progress bar."""
        if self.window and total > 0:
            percent = (current / total) * 100
            self.progress_bar["value"] = percent
            self.progress_label.config(
                text=f"{percent:.1f}% ({current:,} / {total:,} bytes)"
            )
            self.window.update_idletasks()

    def _start_download(self):
        """Start the download process."""
        board_id = self.board_id_var.get().strip()
        if not board_id:
            messagebox.showerror(
                "Error", "Please enter a Board ID or select from the list."
            )
            return

        mlb = self.mlb_var.get().strip()
        if not mlb:
            messagebox.showerror("Error", "Please enter an MLB serial number.")
            return

        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return

        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory: {e}")
                return

        # Confirm download
        os_type = self.os_type_var.get()
        diag = self.diagnostics_var.get()
        download_type = "diagnostics" if diag else f"recovery ({os_type})"

        confirm = messagebox.askyesno(
            "Confirm Download",
            f"Download {download_type} for board {board_id}?\n\n"
            f"Board ID: {board_id}\n"
            f"MLB: {mlb}\n"
            f"Output: {output_dir}",
        )

        if not confirm:
            return

        # Start download in background thread
        self.download_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.cancel_event.clear()

        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(board_id, mlb, diag, os_type, output_dir),
        )
        self.download_thread.start()

    def _download_worker(self, board_id, mlb, diag, os_type, output_dir):
        """Worker thread for download process."""
        assert self.macrecovery is not None
        try:
            result = self.macrecovery.download_recovery_image(
                board_id, mlb, diag, os_type, output_dir
            )
            if self.window:
                self.window.after(0, lambda res=result: self._download_complete(res))
        except Exception as e:
            if self.window:
                # Check if it's a cancellation
                if "cancelled" in str(e).lower():
                    self.window.after(0, self._download_cancelled)
                else:
                    self.window.after(0, lambda err=e: self._download_error(str(err)))

    def _download_complete(self, result):
        """Handle download completion."""
        self.download_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.progress_bar["value"] = 100
        self.progress_label.config(text="Download completed!")

        messagebox.showinfo(
            "Download Complete",
            f"Download completed successfully!\n\n"
            f"File: {result['filename']}\n"
            f"Size: {result['size']:,} bytes\n"
            f"Location: {result['filepath']}",
        )

    def _download_error(self, error_message):
        """Handle download error."""
        if self.download_button.winfo_exists():
            self.download_button.config(state=tk.NORMAL)
        if self.cancel_button.winfo_exists():
            self.cancel_button.config(state=tk.DISABLED)
        if self.progress_bar.winfo_exists():
            self.progress_bar["value"] = 0
        if self.progress_label.winfo_exists():
            self.progress_label.config(text="Download failed!")
        if self.window and self.window.winfo_exists():
            messagebox.showerror("Download Error", f"Download failed:\n{error_message}")

    def _download_cancelled(self):
        """Handle download cancellation."""
        if self.download_button.winfo_exists():
            self.download_button.config(state=tk.NORMAL)
        if self.cancel_button.winfo_exists():
            self.cancel_button.config(state=tk.DISABLED)
        if self.progress_bar.winfo_exists():
            self.progress_bar["value"] = 0
        if self.progress_label.winfo_exists():
            self.progress_label.config(text="Download cancelled!")
        if self.status_label.winfo_exists():
            self.status_label.config(text="Download cancelled by user.")

    def _cancel_download(self):
        """Cancel the current download."""
        if messagebox.askyesno(
            "Confirm Cancel", "Are you sure you want to cancel the current operation?"
        ):
            self.cancel_event.set()
            self.status_label.config(text="Cancelling download...")
            self.cancel_button.config(state=tk.DISABLED)

    def _close_window(self):
        """Cancel any ongoing download and close the window."""
        self.cancel_event.set()
        if self.window:
            self.window.destroy()
