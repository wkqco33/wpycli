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


class UnknownCommandError(UsageError):
    def __init__(self, token: str, *, command: Command) -> None:
        super().__init__(
            f"unknown command {token!r} for {command.full_path}", command=command
        )


class UnknownFlagError(UsageError):
    def __init__(self, token: str, *, command: Command) -> None:
        super().__init__(f"unknown flag {token!r}", command=command)
