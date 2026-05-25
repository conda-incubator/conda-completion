"""Exceptions for conda-completion."""

from __future__ import annotations

from conda.exceptions import CondaError


class CondaCompletionError(CondaError):
    """Base exception for conda-completion operations."""


class ManifestNotFoundError(CondaCompletionError):
    """Raised when the completion manifest does not exist."""

    def __init__(self) -> None:
        self.error_message = "Completion data not found"
        self.hints = ["Run 'conda completion generate' to create it"]
        super().__init__(self.error_message)


class ManifestError(CondaCompletionError):
    """Raised when the completion manifest cannot be read or written."""

    def __init__(self, message: str) -> None:
        self.error_message = f"Cannot read completion data: {message}"
        self.hints = [
            "Try regenerating with 'conda completion generate'",
            "If the problem persists, remove the file and regenerate",
        ]
        super().__init__(self.error_message)


class IntrospectionError(CondaCompletionError):
    """Raised when conda's parser cannot be inspected."""

    def __init__(self, message: str) -> None:
        self.error_message = f"Cannot inspect conda commands: {message}"
        self.hints = [
            "Check whether a conda plugin fails to import",
            "Disable or update the failing plugin, then run 'conda completion generate'",
        ]
        super().__init__(self.error_message)


class CompleterBinaryNotFoundError(CondaCompletionError):
    """Raised when the completion engine binary is not found."""

    def __init__(self) -> None:
        self.error_message = "Completion engine binary not found"
        self.hints = [
            "Reinstall conda-completer: conda install conda-completer",
            "For development: pixi run build",
        ]
        super().__init__(self.error_message)


class ShellNotSupportedError(CondaCompletionError):
    """Raised when the requested shell is not supported."""

    def __init__(self, shell: str, available: list[str]) -> None:
        self.error_message = f"Shell '{shell}' is not supported"
        self.hints = [f"Supported shells: {', '.join(sorted(available))}"]
        super().__init__(self.error_message)
