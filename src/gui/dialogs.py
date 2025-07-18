"""
gibMacOS GUI
https://github.com/HelllGuest/gibMacOS_GUI

Original gibMacOS by corpnewt: https://github.com/corpnewt/gibMacOS
macrecovery.py by acidanthera team: https://github.com/acidanthera/OpenCorePkg

GUI Author: Anoop Kumar
License: MIT
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from src.utils.helpers import center_window, open_url


class AboutDialog:
    """About dialog showing application information and links."""

    def __init__(self, parent):
        self.parent = parent
        self.window = None

    def show(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("About")
        self.window.transient(self.parent)
        self.window.grab_set()

        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # App name, version, description (centered)
        ttk.Label(main_frame, text="gibMacOS GUI", font=("Segoe UI", 28, "bold")).pack(
            anchor="center"
        )
        ttk.Label(main_frame, text="Beta 1.0", font=("Segoe UI", 14)).pack(
            anchor="center", pady=(0, 10)
        )
        desc = (
            "gibMacOS GUI is a free and open source macOS recovery/installer downloader, "
            "based on corpnewt's gibMacOS and macrecovery.py.\n\n"
            "It uses only official Apple servers and supports both full installers and recovery images.\n\n"
            "This project is not affiliated with Apple Inc."
        )
        ttk.Label(main_frame, text=desc, wraplength=400, justify="center").pack(
            anchor="center"
        )

        links_frame = ttk.Frame(main_frame)
        links_frame.pack(anchor="center", pady=(10, 0))

        def make_centered_link(text, url):
            lbl = tk.Label(
                links_frame,
                text=text,
                fg="blue",
                cursor="hand2",
                font=("Segoe UI", 10, "underline"),
            )
            lbl.pack(side=tk.LEFT, padx=20)
            lbl.bind("<Button-1>", lambda e: open_url(url))

        make_centered_link("Source code", "https://github.com/HelllGuest/gibMacOS_GUI")
        make_centered_link("gibMacOS", "https://github.com/corpnewt/gibMacOS")
        make_centered_link(
            "License", "https://github.com/HelllGuest/gibMacOS_GUI/blob/main/LICENSE"
        )

        credits_frame = ttk.LabelFrame(
            main_frame, text="Credits & License", padding=(10, 8)
        )
        credits_frame.pack(anchor="center", pady=(12, 0))
        credits_text = (
            "Credits: corpnewt (original gibMacOS), acidanthera team (macrecovery.py), "
            "and Anoop Kumar (GUI & integration)."
        )
        ttk.Label(
            credits_frame,
            text=credits_text,
            wraplength=380,
            justify="center",
            font=("Segoe UI", 9),
        ).pack(anchor="center", pady=(0, 2))
        license_text = "This software is released under the MIT License and is free to use, distribute, and modify."
        ttk.Label(
            credits_frame,
            text=license_text,
            wraplength=380,
            justify="center",
            font=("Segoe UI", 9),
        ).pack(anchor="center", pady=(0, 0))

        self.window.update_idletasks()
        min_width = main_frame.winfo_reqwidth() + 40
        min_height = main_frame.winfo_reqheight() + 40
        self.window.minsize(min_width, min_height)
        center_window(self.parent, self.window)
        self.window.resizable(True, True)


class HowToUseDialog:
    """How to use dialog with comprehensive instructions."""

    def __init__(self, parent):
        self.parent = parent
        self.window = None

    def show(self):
        """Show the how to use dialog."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("How to Use")
        self.window.geometry("700x600")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Create main scrollable frame
        main_canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(
            self.window, orient="vertical", command=main_canvas.yview
        )
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")),
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        main_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Basic Usage section
        basic_frame = ttk.LabelFrame(scrollable_frame, text="Basic Usage", padding=15)
        basic_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        basic_text = """Step 1: Configure Settings
   • Select Catalog Type: Choose from Public Release, Beta, Customer Seed, or Developer
   • Set Max macOS Version: Enter the highest version you want to see (e.g., 14 for macOS Sonoma)
   • Toggle "Show Recovery Only" if you only want recovery packages

Step 2: Load Available Products
   • Click "Refresh Products" to download the catalog and populate the list
   • Wait for the status to show "Found X items"

Step 3: Select and Download
   • Browse the list and select your desired macOS installer
   • Choose download directory (defaults to ~/Downloads)
   • Click "Download Selected" to start downloading
   • Monitor progress in the status bar and console log

Step 4: Use Downloaded Files
   • Find your downloaded files in the specified directory
   • Each product creates its own subfolder with the Product ID name
   • Use the files to create bootable installers or recovery media"""

        ttk.Label(basic_frame, text=basic_text, justify=tk.LEFT, wraplength=650).pack(
            anchor=tk.W
        )

        # Advanced Usage section
        advanced_frame = ttk.LabelFrame(
            scrollable_frame, text="Advanced Usage", padding=15
        )
        advanced_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        advanced_text = """Catalog Management
   • Public Release: Standard macOS releases available to all users
   • Beta: Pre-release versions for beta testers
   • Customer Seed: Special releases for registered developers
   • Developer: Latest developer previews (requires developer account)

Filtering and Sorting
   • Use column headers to sort by Name, Version, Build, Size, or Product ID
   • Click column headers multiple times to toggle ascending/descending order
   • "Show Recovery Only" filters to show only recovery packages (not full installers)
   • Version filtering automatically excludes versions higher than your specified maximum

Download Options
   • Save Catalog Locally: Caches catalog data for faster subsequent loads
   • Force Local Catalog Re-download: Forces refresh of cached catalog data
   • Caffeinate Downloads: Prevents system sleep during downloads (macOS only)
   • Console Log: Shows detailed download progress and error information

macOS Integration (macOS only)
   • Set SU CatalogURL: Configures Software Update to use the selected catalog
   • Clear SU CatalogURL: Restores default Software Update catalog
   • These options require administrator privileges

Troubleshooting
   • If downloads fail, check your internet connection
   • Large files may take significant time to download
   • Use the console log to diagnose download issues
   • Ensure sufficient disk space in your download directory"""

        ttk.Label(
            advanced_frame, text=advanced_text, justify=tk.LEFT, wraplength=650
        ).pack(anchor=tk.W)

        # macrecovery section
        macrecovery_frame = ttk.LabelFrame(
            scrollable_frame, text="macrecovery", padding=15
        )
        macrecovery_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        macrecovery_text = """macrecovery Feature
   • Based on macrecovery.py by vit9696
   • Downloads recovery images directly from Apple's servers
   • Hardware-specific downloads for different Mac models
   • Supports both recovery images and diagnostic tools

Accessing macrecovery
   • Click "macrecovery" button in main interface
   • Or use File → macrecovery from menu
   • Available board IDs are loaded from macrecovery's database

Board Selection
   • Dropdown Method: Select from comprehensive list of Mac board IDs
   • Manual Entry: Enter board ID manually if not in list
   • Format: Mac-XXXXXXXXXXXXXX (e.g., Mac-7BA5B2D9E42DDD94)
   • Shows macOS version for each board automatically

Download Options
   • OS Type: Choose "default" (standard) or "latest" (most recent)
   • Diagnostics: Toggle to download diagnostic tools instead of recovery
   • MLB Serial: Usually 00000000000000000 (default)
   • Output Directory: Select custom download location

Use Cases
   • System Recovery: Download recovery images for specific Mac models
   • Diagnostics: Download Apple's diagnostic tools
   • Hackintosh: Get recovery images for custom configurations
   • Hardware Testing: Access diagnostic tools for troubleshooting

Technical Details
   • Uses Apple's osrecovery.apple.com servers
   • Implements authentication and session management
   • Supports chunklist verification for file integrity
   • Downloads are hardware-specific and model-appropriate"""

        ttk.Label(
            macrecovery_frame, text=macrecovery_text, justify=tk.LEFT, wraplength=650
        ).pack(anchor=tk.W)

        # Tips and Best Practices section
        tips_frame = ttk.LabelFrame(
            scrollable_frame, text="Tips & Best Practices", padding=15
        )
        tips_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        tips_text = """Performance Tips
   • Use "Save Catalog Locally" for faster repeated access
   • Close other bandwidth-intensive applications during downloads
   • Use a wired internet connection for large downloads

Storage Management
   • macOS installers can be 12-15 GB each
   • Recovery packages are typically 500MB-2GB
   • Plan your storage accordingly
   • Consider using external storage for large collections

Version Selection
   • Latest versions are at the top when sorted by version
   • Check build numbers for specific releases
   • Recovery packages are useful for system recovery
   • Full installers are needed for clean installations

Security Notes
   • All downloads come directly from Apple's servers
   • Verify file integrity before use
   • Keep downloaded files in a secure location
   • Use official Apple tools to create bootable media"""

        ttk.Label(tips_frame, text=tips_text, justify=tk.LEFT, wraplength=650).pack(
            anchor=tk.W
        )

        # File Types section
        files_frame = ttk.LabelFrame(
            scrollable_frame, text="Understanding File Types", padding=15
        )
        files_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        files_text = """InstallAssistant Packages
   • Full macOS installers (12-15 GB)
   • Contains complete macOS installation files
   • Used for clean installations and upgrades
   • Can be used to create bootable USB installers

Recovery Packages
   • Smaller recovery-only packages (500MB-2GB)
   • Contains recovery tools and basic system files
   • Used for system recovery and troubleshooting
   • Can be used to create recovery media

Package Contents
   • .pkg files: Apple package installers
   • .dmg files: Disk images containing installers
   • .dist files: Distribution files with installation scripts
   • Metadata files: Information about the installer

Usage Scenarios
   • Full Installer: New installations, major upgrades
   • Recovery Package: System recovery, minor repairs
   • Both: Complete system management toolkit"""

        ttk.Label(files_frame, text=files_text, justify=tk.LEFT, wraplength=650).pack(
            anchor=tk.W
        )

        # Close button
        ttk.Button(self.window, text="Close", command=self.window.destroy).pack(pady=10)

        # Center window
        center_window(self.parent, self.window)

        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.window.bind("<MouseWheel>", _on_mousewheel)


class HelpDialog:
    """Help dialog providing documentation and support resources for gibMacOS GUI."""

    def __init__(self, parent):
        self.parent = parent
        self.window = None

    def show(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Help")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Main frame with scrollable content
        main_canvas = tk.Canvas(self.window, borderwidth=0)
        scrollbar = ttk.Scrollbar(
            self.window, orient="vertical", command=main_canvas.yview
        )
        scrollable_frame = ttk.Frame(main_canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")),
        )
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        main_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Heading
        heading = tk.Label(
            scrollable_frame,
            text="Welcome to gibMacOS GUI Help",
            font=("Segoe UI", 16, "bold"),
            anchor="w",
            justify=tk.LEFT,
        )
        heading.pack(anchor="w", pady=(0, 10))

        # Section: Documentation
        doc_heading = tk.Label(
            scrollable_frame,
            text="Documentation",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            justify=tk.LEFT,
        )
        doc_heading.pack(anchor="w", pady=(0, 2))

        def link(text, url):
            label = tk.Label(
                scrollable_frame,
                text=text,
                fg="blue",
                cursor="hand2",
                font=("Segoe UI", 10, "underline"),
                anchor="w",
                justify=tk.LEFT,
            )
            label.bind("<Button-1>", lambda e: open_url(url))
            return label

        # Documentation paragraphs
        tk.Label(
            scrollable_frame,
            text="You can find gibMacOS GUI documentation on the project's ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 0))
        link("wiki", "https://github.com/HelllGuest/gibMacOS_GUI/wiki").pack(anchor="w")
        tk.Label(scrollable_frame, text=" website.", anchor="w", justify=tk.LEFT).pack(
            anchor="w"
        )

        tk.Label(
            scrollable_frame,
            text="\nIf you are a newcomer to gibMacOS GUI, please read the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link(
            "Introduction to gibMacOS GUI",
            "https://github.com/HelllGuest/gibMacOS_GUI/wiki/Introduction",
        ).pack(anchor="w")
        tk.Label(scrollable_frame, text=".\n", anchor="w", justify=tk.LEFT).pack(
            anchor="w"
        )

        tk.Label(
            scrollable_frame,
            text="You will find some information on how to use the app in the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link(
            '"How to use gibMacOS GUI"',
            "https://github.com/HelllGuest/gibMacOS_GUI/wiki/How-to-Use",
        ).pack(anchor="w")
        tk.Label(
            scrollable_frame, text=" document.\n", anchor="w", justify=tk.LEFT
        ).pack(anchor="w")

        tk.Label(
            scrollable_frame,
            text="For all the downloading, verification, and recovery tasks, you should find useful information in the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link(
            "Advanced Usage",
            "https://github.com/HelllGuest/gibMacOS_GUI/wiki/Advanced-Usage",
        ).pack(anchor="w")
        tk.Label(
            scrollable_frame, text=" section.\n", anchor="w", justify=tk.LEFT
        ).pack(anchor="w")

        tk.Label(
            scrollable_frame,
            text="If you are unsure about terminology, please consult the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link(
            "knowledge base", "https://github.com/HelllGuest/gibMacOS_GUI/wiki/Glossary"
        ).pack(anchor="w")
        tk.Label(scrollable_frame, text=".\n", anchor="w", justify=tk.LEFT).pack(
            anchor="w"
        )

        tk.Label(
            scrollable_frame,
            text="To understand the main keyboard shortcuts, read the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link(
            "shortcuts page",
            "https://github.com/HelllGuest/gibMacOS_GUI/wiki/Shortcuts",
        ).pack(anchor="w")
        tk.Label(scrollable_frame, text=".\n", anchor="w", justify=tk.LEFT).pack(
            anchor="w"
        )

        # Section: Help
        help_heading = tk.Label(
            scrollable_frame,
            text="Help",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            justify=tk.LEFT,
        )
        help_heading.pack(anchor="w", pady=(10, 2))

        tk.Label(
            scrollable_frame,
            text="Before asking any question, please refer yourself to the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link("FAQ", "https://github.com/HelllGuest/gibMacOS_GUI/wiki/FAQ").pack(
            anchor="w"
        )
        tk.Label(scrollable_frame, text=".\n", anchor="w", justify=tk.LEFT).pack(
            anchor="w"
        )

        tk.Label(
            scrollable_frame,
            text="You might then get (and give) help on the ",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")
        link(
            "Discussions", "https://github.com/HelllGuest/gibMacOS_GUI/discussions"
        ).pack(anchor="w")
        tk.Label(scrollable_frame, text=", the ", anchor="w", justify=tk.LEFT).pack(
            anchor="w"
        )
        link(
            "mailing-lists", "https://github.com/HelllGuest/gibMacOS_GUI#contact"
        ).pack(anchor="w")
        tk.Label(
            scrollable_frame,
            text=" or our IRC channel (see project README).",
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w")

        # Close button
        close_btn = ttk.Button(self.window, text="Close", command=self.window.destroy)
        close_btn.pack(side=tk.BOTTOM, anchor="e", padx=15, pady=10)

        # Center window
        center_window(self.parent, self.window)

        # Mouse wheel scroll
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.window.bind("<MouseWheel>", _on_mousewheel)


def ask_overwrite_file(parent, file_path):
    """Show a Yes/No dialog asking if the user wants to overwrite an existing file."""
    filename = os.path.basename(file_path)
    return messagebox.askyesno(
        "File Exists",
        f'The file "{filename}" already exists.\nDo you want to overwrite it?',
        parent=parent,
        icon=messagebox.WARNING,
    )
