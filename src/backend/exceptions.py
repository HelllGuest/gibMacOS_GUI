"""
Exception classes for gibMacOSGUI.

Defines custom exceptions used throughout the application.
"""


class ProgramError(Exception):
    """Base exception for program errors with custom title."""

    def __init__(self, message, title="Error"):
        super().__init__(message)
        self.title = title


class CancelledError(ProgramError):
    """Exception raised when operation is cancelled by user."""

    def __init__(self, message="Operation cancelled by user."):
        super().__init__(message, title="Operation Cancelled")
