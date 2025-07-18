#!/usr/bin/env python3
"""
gibMacOS GUI
https://github.com/HelllGuest/gibMacOS_GUI

Original gibMacOS by corpnewt: https://github.com/corpnewt/gibMacOS
macrecovery.py by acidanthera team: https://github.com/acidanthera/OpenCorePkg

GUI Author: Anoop Kumar
License: MIT
"""

import importlib.util
import logging
import sys
from pathlib import Path

# Setup paths first
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
scripts_path = PROJECT_ROOT

# Add scripts path to sys.path if not already there
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

# Check for required modules using importlib
required_modules = ["downloader", "utils", "plistlib"]
missing_modules = []

for module in required_modules:
    if not importlib.util.find_spec(module):
        missing_modules.append(module)

if missing_modules:
    print(f"ERROR: Failed to import required modules: {', '.join(missing_modules)}")
    print(f"Make sure the gibMacOS directory exists at: {scripts_path}")
    sys.exit(1)

# Import after path setup and module checks
try:
    from src.gui.gibmacos_gui import GibMacOSGUI  # noqa: E402
except ImportError:
    print(
        "ERROR: Failed to import GibMacOSGUI. Make sure all dependencies are installed."
    )
    sys.exit(1)


def main() -> None:
    """Main entry point for the application."""
    if not scripts_path.exists():
        print(
            "ERROR: project root directory not found. Use run_gui.py for proper setup."
        )
        sys.exit(1)
    app = GibMacOSGUI()
    app.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
