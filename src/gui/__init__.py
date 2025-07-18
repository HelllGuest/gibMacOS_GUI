"""
GUI package for gibMacOS.

Contains the Tkinter-based user interface components.
"""

from .dialogs import AboutDialog, HowToUseDialog
from .gibmacos_gui import GibMacOSGUI

__all__ = ["GibMacOSGUI", "AboutDialog", "HowToUseDialog"]
