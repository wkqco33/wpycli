from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TextIO

from .output import Terminal

if TYPE_CHECKING:
    from .command import Command

RunHandler = Callable[["CommandContext"], int | None]
HookHandler = Callable[["CommandContext"], None]
ArgsValidator = Callable[[list[str]], None]


@dataclass(slots=True)
class CommandContext:
    command: Command
    argv: list[str]
    args: list[str]
    flags: dict[str, Any]
    config: Any = None
    logger: logging.Logger | None = None
    terminal: Terminal | None = None
    stdout: TextIO | None = None
    stderr: TextIO | None = None
