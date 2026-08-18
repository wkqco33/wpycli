from __future__ import annotations

import itertools
import sys
from typing import Self, TextIO

from .utils import visual_width

_SPINNER_FRAMES = ("|", "/", "-", "\\")


def _is_tty(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(callable(isatty) and isatty())


class Spinner:
    """Terminal spinner for indicating progress during synchronous operations."""

    def __init__(self, message: str, *, stream: TextIO | None = None) -> None:
        self.message = message
        self._stream = stream if stream is not None else sys.stdout
        self._is_tty = _is_tty(self._stream)
        self._frames = itertools.cycle(_SPINNER_FRAMES)
        self._done = False

    def __enter__(self) -> Self:
        if not self._is_tty:
            self._stream.write(f"{self.message}...\n")
            self._stream.flush()
        return self

    def tick(self) -> None:
        if not self._is_tty or self._done:
            return
        frame = next(self._frames)
        self._stream.write(f"\r{frame} {self.message}")
        self._stream.flush()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._done = True
        if self._is_tty:
            clear_width = visual_width(self.message) + 4
            self._stream.write("\r" + " " * clear_width + "\r")
            self._stream.flush()


class ProgressBar:
    """Terminal progress bar with TTY and non-TTY fallback rendering."""

    def __init__(
        self, total: int, *, width: int = 30, stream: TextIO | None = None
    ) -> None:
        if total <= 0:
            raise ValueError("total must be positive")
        if width <= 0:
            raise ValueError("width must be positive")
        self.total = total
        self.current = 0
        self._width = width
        self._stream = stream if stream is not None else sys.stdout
        self._is_tty = _is_tty(self._stream)
        self._last_reported_percent = -1

    def __enter__(self) -> Self:
        self._render()
        return self

    def update(self, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("amount must not be negative")
        self.current = min(self.total, self.current + amount)
        self._render()

    def _render(self) -> None:
        percent = int(self.current / self.total * 100)
        filled = int(self._width * self.current / self.total)
        bar = "#" * filled + "-" * (self._width - filled)
        line = f"[{bar}] {percent}%"

        if self._is_tty:
            self._stream.write(f"\r{line}")
            self._stream.flush()
            return

        if percent - self._last_reported_percent >= 10 or percent == 100:
            self._stream.write(f"{line}\n")
            self._stream.flush()
            self._last_reported_percent = percent

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._is_tty:
            self._stream.write("\n")
            self._stream.flush()
