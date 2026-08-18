from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TextIO

from .utils import visual_width, visual_wrap

_ANSI_CODES = {
    # Text decoration
    "bold": "1",
    "dim": "2",
    "italic": "3",
    "underline": "4",
    "strikethrough": "9",
    # Standard colors
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    # Bright colors
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}
_KIND_STYLES = {
    "info": ("cyan", "bold"),
    "success": ("green", "bold"),
    "warning": ("yellow", "bold"),
    "error": ("red", "bold"),
}


@dataclass(slots=True)
class Terminal:
    stream: TextIO | None = None
    force_color: bool | None = None
    width: int = 88

    @property
    def supports_color(self) -> bool:
        if self.force_color is not None:
            return self.force_color
        if os.environ.get("NO_COLOR"):
            return False
        if self.stream is None:
            return False
        isatty = getattr(self.stream, "isatty", None)
        if not callable(isatty) or not isatty():
            return False
        return os.environ.get("TERM", "dumb") != "dumb"

    def style(self, text: str, *styles: str) -> str:
        if not self.supports_color or not styles:
            return text
        codes = [code for style in styles if (code := _ANSI_CODES.get(style))]
        if not codes:
            return text
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"

    def section(self, title: str) -> str:
        return self.style(title.upper(), "bold", "cyan")

    def muted(self, text: str) -> str:
        return self.style(text, "dim")

    def highlight(self, text: str) -> str:
        return self.style(text, "bold", "green")

    def panel(
        self,
        title: str,
        body: str | Sequence[str],
        *,
        accent: str = "cyan",
    ) -> str:
        lines = self._wrap_lines(body)
        stripped_widths = [visual_width(line) for line in lines]
        visible_width = max(stripped_widths, default=0)

        title_width = visual_width(title)
        title_text = f" {title} "
        title_text_width = title_width + 2

        visible_width = max(visible_width, title_text_width)
        horizontal = "-" * (visible_width + 2)
        top = f"+{horizontal}+"
        if title_text_width <= len(horizontal):
            top = f"+{title_text}{'-' * (visible_width + 2 - title_text_width)}+"
        bottom = f"+{horizontal}+"
        if accent:
            top = self.style(top, accent, "bold")
            bottom = self.style(bottom, accent, "bold")

        rendered = [top]
        for line, width in zip(lines, stripped_widths):
            rendered.append(f"| {line}{' ' * (visible_width - width)} |")
        rendered.append(bottom)
        return "\n".join(rendered)

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        accent: str = "cyan",
    ) -> str:
        columns = len(headers)
        str_rows = [[str(cell) for cell in row] for row in rows]
        widths = [visual_width(header) for header in headers]
        for row in str_rows:
            for i in range(columns):
                cell_width = visual_width(row[i]) if i < len(row) else 0
                widths[i] = max(widths[i], cell_width)

        def _render_row(cells: Sequence[str]) -> str:
            parts = []
            for i in range(columns):
                cell = cells[i] if i < len(cells) else ""
                parts.append(f"{cell}{' ' * (widths[i] - visual_width(cell))}")
            return "  ".join(parts).rstrip()

        header_text = _render_row(headers)
        lines = [
            self.style(header_text, accent, "bold"),
            self.style("-" * visual_width(header_text), accent),
        ]
        lines.extend(_render_row(row) for row in str_rows)
        return "\n".join(lines)

    def confirm(self, message: str, *, default: bool = False) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            raw = input(f"{message} {suffix} ").strip().lower()
            if not raw:
                return default
            if raw in {"y", "yes"}:
                return True
            if raw in {"n", "no"}:
                return False

    def prompt(self, message: str, *, secret: bool = False) -> str:
        if secret:
            import getpass

            return getpass.getpass(message)
        return input(message)

    def definition_list(self, rows: Sequence[tuple[str, str]]) -> str:
        if not rows:
            return ""
        label_widths = [visual_width(label) for label, _ in rows]
        label_width = max(label_widths, default=0)
        lines: list[str] = []
        for (label, description), width in zip(rows, label_widths):
            padded = f"{label}{' ' * (label_width - width)}"
            lines.append(f"  {self.highlight(padded)}  {description}".rstrip())
        return "\n".join(lines)

    def message(self, kind: str, title: str, body: str) -> str:
        styles = _KIND_STYLES.get(kind, ("bold",))
        label = self.style(title, *styles)
        return self.panel(label, body, accent=styles[0] if styles else "cyan")

    def pretty_json(self, text: str) -> str:
        lines = text.splitlines() or [text]
        rendered: list[str] = []
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            prefix = " " * indent
            if stripped.startswith(("{", "}", "[", "]")):
                rendered.append(prefix + self.style(stripped, "magenta"))
            elif ":" in stripped:
                key, rest = stripped.split(":", 1)
                rendered.append(prefix + self.style(key, "cyan") + ":" + rest)
            else:
                rendered.append(line)
        return "\n".join(rendered)

    def _wrap_lines(self, body: str | Sequence[str]) -> list[str]:
        raw_lines = body.splitlines() if isinstance(body, str) else list(body)
        if not raw_lines:
            return [""]
        width = max(20, self.width - 6)
        lines: list[str] = []
        for raw_line in raw_lines:
            if not raw_line:
                lines.append("")
                continue
            wrapped = visual_wrap(raw_line, width)
            lines.extend(wrapped or [""])
        return lines
