"""
Helper utility functions for gibMacOS GUI.

Contains various utility functions used throughout the application.
"""

import logging
import os
import platform
import subprocess
import webbrowser
from pathlib import Path


def get_time_string(seconds: float) -> str:
    """Return a human-readable time string from seconds."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"


def open_directory(path: str) -> None:
    """Open a directory in the system's file explorer."""
    path_obj = Path(path)
    if not path_obj.exists():
        logging.error(f"Directory does not exist: {path}")
        return

    try:
        if platform.system() == "Windows":
            # Use explorer command for Windows
            subprocess.run(["explorer", str(path_obj)], check=False)
        elif platform.system() == "Darwin":
            # Use open command for macOS
            subprocess.run(["open", str(path_obj)], check=False)
        else:
            # Use xdg-open for Linux and other Unix-like systems
            subprocess.run(["xdg-open", str(path_obj)], check=False)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logging.error(f"Failed to open directory {path}: {e}")
        # Fallback for Windows if explorer fails
        if platform.system() == "Windows":
            try:
                os.startfile(str(path_obj))
            except OSError as fallback_error:
                logging.error(f"Fallback also failed: {fallback_error}")


def open_url(url: str) -> None:
    """Open a URL in the default web browser."""
    webbrowser.open(url)


def center_window(parent_window, child_window) -> None:
    """Center a child window relative to its parent window."""
    child_window.update_idletasks()
    x = (
        parent_window.winfo_x()
        + (parent_window.winfo_width() // 2)
        - (child_window.winfo_width() // 2)
    )
    y = (
        parent_window.winfo_y()
        + (parent_window.winfo_height() // 2)
        - (child_window.winfo_height() // 2)
    )
    child_window.geometry(f"+{x}+{y}")


def get_system_info() -> str:
    """Return a string with basic system information."""
    return f"{platform.system()} {platform.release()} ({platform.version()})"
