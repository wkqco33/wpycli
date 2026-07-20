from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .command import Command


class CLIError(RuntimeError):
    def __init__(
        self, message: str, *, exit_code: int = 2, command: Command | None = None
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.command = command


class UsageError(CLIError):
    pass


def _with_suggestion(message: str, suggestion: str | None) -> str:
    if not suggestion:
        return message
    return f"{message}\n\nDid you mean this?\n\t{suggestion}"


class UnknownCommandError(UsageError):
    def __init__(
        self, token: str, *, command: Command, suggestion: str | None = None
    ) -> None:
        message = f"unknown command {token!r} for {command.full_path}"
        super().__init__(_with_suggestion(message, suggestion), command=command)


class UnknownFlagError(UsageError):
    def __init__(
        self, token: str, *, command: Command, suggestion: str | None = None
    ) -> None:
        message = f"unknown flag {token!r}"
        super().__init__(_with_suggestion(message, suggestion), command=command)


class BootstrapError(CLIError):
    """Raised when config/logging bootstrap fails for a user-actionable reason."""
