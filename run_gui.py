#!/usr/bin/env python3
"""
gibMacOS GUI Launcher

This script sets up the environment and launches the gibMacOS GUI application.
It handles dependency installation, repository setup, and application startup.

Version: Beta 1.0
Author: Anoop Kumar
License: MIT
"""

import argparse
import glob
import importlib.util
import logging
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import List

# Configuration
GIB_REPO_URL = "https://github.com/corpnewt/gibMacOS"
GIB_DIR = "gibMacOS"
SCRIPT_DIR = Path(__file__).parent.resolve()

# Required Python packages
REQUIRED_PACKAGES: List[str] = [
    "requests",
    'pyobjc;platform_system=="Darwin"',  # macOS only
    "tk",
]


def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    if sys.version_info < (3, 7):
        print(f"ERROR: Python 3.7+ required. Current version: {sys.version}")
        print("Please upgrade Python and try again.")
        return False
    print(f"Python version check passed: {sys.version}")
    return True


def check_tkinter() -> bool:
    """Check if tkinter is available."""
    if importlib.util.find_spec("tkinter"):
        print("Tkinter check passed.")
        return True
    else:
        print("ERROR: Tkinter is not available.")
        print("\nTo install Tkinter:")
        if platform.system() == "Windows":
            print("  - Reinstall Python and ensure 'tcl/tk and IDLE' is selected")
        elif platform.system() == "Darwin":
            print("  - Tkinter should be included with Python on macOS")
        else:  # Linux
            print("  - Ubuntu/Debian: sudo apt-get install python3-tk")
            print("  - Fedora: sudo dnf install python3-tkinter")
            print("  - Arch: sudo pacman -S tk")
        return False


def check_git() -> bool:
    """Check if git is available."""
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def download_manual_fallback() -> bool:
    """Provide manual download instructions when git is not available."""
    print("\n" + "=" * 60)
    print("GIT NOT FOUND - Manual Setup Required")
    print("=" * 60)
    print("Please manually download the gibMacOS repository:")
    print(f"1. Visit: {GIB_REPO_URL}")
    print("2. Click the green 'Code' button")
    print("3. Select 'Download ZIP'")
    print(f"4. Extract the ZIP file to: {SCRIPT_DIR}")
    print(f"5. Rename the extracted folder to: {GIB_DIR}")
    print("\nExpected structure:")
    print(f"  {SCRIPT_DIR}/")
    print(f"  ├── {GIB_DIR}/")
    print("  │   ├── Scripts/")
    print("  │   └── ...")
    print("  ├── src/")
    print("  └── run_gui.py")
    print("\nAfter manual setup, run this script again.")
    print("=" * 60)
    return False


def main() -> None:
    """Main entry point for the bootstrap process."""
    print("Setting up gibMacOS GUI environment...")
    if not check_python_version():
        sys.exit(1)
    if not check_tkinter():
        sys.exit(1)
    try:
        if not install_dependencies():
            print("Failed to install dependencies. Exiting.")
            sys.exit(1)
        if not setup_gib_repo():
            print("Failed to setup gibMacOS repository. Exiting.")
            sys.exit(1)
        if not copy_custom_files():
            print("Failed to copy custom files. Exiting.")
            sys.exit(1)
        launch_gui()
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during setup: {e}")
        sys.exit(1)


def install_dependencies() -> bool:
    """Install required Python packages using pip with retry mechanism."""
    print("\nChecking and installing required dependencies...")
    pip_cmd = [sys.executable, "-m", "pip"]
    try:
        subprocess.run(
            [*pip_cmd, "--version"], check=True, capture_output=True, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: pip is not available. Please install pip first.")
        return False
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            print("Upgrading pip...")
            subprocess.run(
                [*pip_cmd, "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                text=True,
            )
            for package in REQUIRED_PACKAGES:
                package_name = package.split(";")[0]
                print(f"Installing {package_name}...")
                subprocess.run(
                    [*pip_cmd, "install", package],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            print("All dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1:
                print(
                    f"\nAttempt {attempt + 1} failed. Retrying in {retry_delay} seconds..."
                )
                if e.stderr:
                    print(f"Error details: {e.stderr}")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(
                    f"\nERROR: Failed to install dependencies after {max_retries} attempts: {e}"
                )
                if e.stderr:
                    print(f"Error details: {e.stderr}")
                return False
        except Exception as e:
            print(f"\nERROR: Unexpected error during dependency installation: {e}")
            return False
    return False  # Fallback return for any unexpected cases


def setup_gib_repo() -> bool:
    """Clone or update the gibMacOS repository with git fallback."""
    try:
        gib_path = SCRIPT_DIR / GIB_DIR
        if gib_path.exists():
            print(f"\nFound existing gibMacOS repository at {gib_path}")
            if (gib_path / ".git").exists():
                if check_git():
                    print("Updating existing repository...")
                    try:
                        subprocess.run(
                            ["git", "pull"],
                            cwd=gib_path,
                            check=True,
                            capture_output=True,
                            text=True,
                        )
                        print("Repository updated successfully.")
                        return True
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to update repository: {e}")
                        print("Continuing with existing files...")
                        return True
                else:
                    print("Git not available, using existing files...")
                    return True
            else:
                print("Existing directory found but not a git repository.")
                print("Continuing with existing files...")
                return True
        if check_git():
            print(f"\nCloning gibMacOS repository to {gib_path}...")
            max_retries = 3
            retry_delay = 2
            for attempt in range(max_retries):
                try:
                    subprocess.run(
                        ["git", "clone", GIB_REPO_URL, str(gib_path)],
                        cwd=SCRIPT_DIR,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print("Repository cloned successfully.")
                    return True
                except subprocess.CalledProcessError as e:
                    if attempt < max_retries - 1:
                        print(
                            f"\nAttempt {attempt + 1} failed. Retrying in {retry_delay} seconds..."
                        )
                        if e.stderr:
                            print(f"Error details: {e.stderr}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        print(
                            f"\nFailed to clone repository after {max_retries} attempts: {e}"
                        )
                        if e.stderr:
                            print(f"Error details: {e.stderr}")
                        return download_manual_fallback()
        else:
            return download_manual_fallback()
    except Exception as e:
        print(f"\nUnexpected error during repository setup: {e}")
        return False
    return False  # Fallback return for any unexpected cases


def copy_custom_files() -> bool:
    """Copy custom files to the gibMacOS directory."""
    try:
        gib_path = SCRIPT_DIR / GIB_DIR
        if not gib_path.exists():
            print(f"\nERROR: gibMacOS directory not found at {gib_path}")
            print("Please ensure the repository setup completed successfully.")
            return False
        file_mappings = [("src/downloader.py", gib_path / "Scripts" / "downloader.py")]
        for src_rel, dst in file_mappings:
            src = SCRIPT_DIR / src_rel
            if not src.exists():
                print(f"\nWarning: Source file not found: {src}")
                continue
            print(f"\nCopying {src_rel} to {dst}")
            shutil.copy2(src, dst)
            if platform.system() != "Windows":
                dst.chmod(dst.stat().st_mode | stat.S_IEXEC)
        print("Custom files copied successfully.")
        return True
    except Exception as e:
        print(f"\nFile copy failed: {e}")
        return False


def launch_gui() -> None:
    """Launch the gibMacOS GUI application."""
    try:
        main_script = SCRIPT_DIR / "src" / "main.py"
        if not main_script.exists():
            print(f"\nERROR: Main script not found at {main_script}")
            print("Please ensure the setup completed successfully.")
            sys.exit(1)
        print(f"\nLaunching gibMacOS GUI from {main_script}...")
        subprocess.run([sys.executable, str(main_script)], cwd=SCRIPT_DIR)
    except subprocess.CalledProcessError as e:
        print(f"\nFailed to launch GUI: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error launching GUI: {e}")
        sys.exit(1)


def cleanup_workspace() -> None:
    """Remove unrelated/temporary files and folders."""
    # Folders to remove if present
    folder_targets = [
        "gibMacOS",
        "screenshots",
        "downloads",
        "catalog_cache",
        "logs",
        "temp",
        "tmp",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".nox",
        ".vscode",
        ".idea",
        "__pycache__",
    ]
    # File patterns to remove from project root
    file_patterns = [
        "*.log",
        "*.tmp",
        "*.bak",
        "*.old",
        "*.sqlite",
        "*.sqlite3",
        "*.db",
        "*.egg-info",
        "*.pyc",
        "*.pyo",
        "*.swp",
        "*.swo",
        "*~",
        "settings.json",
        "config.json",
    ]
    removed = []
    # Remove folders in project root
    for folder in folder_targets:
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
            removed.append(folder + "/ (dir)")
    # Remove __pycache__ recursively
    for root, dirs, files in os.walk(".", topdown=False):
        for d in dirs:
            if d == "__pycache__":
                pycache_path = os.path.join(root, d)
                shutil.rmtree(pycache_path, ignore_errors=True)
                removed.append(os.path.relpath(pycache_path) + "/ (dir, recursive)")
    # Remove files matching patterns in project root
    for pattern in file_patterns:
        for file in glob.glob(pattern):
            if os.path.isfile(file):
                os.remove(file)
                removed.append(file)
    print("Cleanup complete. Removed:")
    for r in removed:
        print(f"  - {r}")
    if not removed:
        print("Nothing to clean up.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="gibMacOS GUI launcher")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove all files/folders created during the running of this project (temp, cache, logs, downloads, venv, etc.) and exit",
    )
    args, unknown = parser.parse_known_args()
    if args.cleanup:
        cleanup_workspace()
        sys.exit(0)
    main()
