"""
Backend package for gibMacOS GUI.

Contains the business logic for macOS installer downloads and catalog management.
"""

from .exceptions import CancelledError, ProgramError
from .gibmacos_backend import GibMacOSBackend
from .internet_recovery import MacRecovery

__all__ = ["ProgramError", "CancelledError", "GibMacOSBackend", "MacRecovery"]
