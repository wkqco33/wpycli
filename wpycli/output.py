from __future__ import annotations

from dataclasses import dataclass
import os
import re
import textwrap
from typing import Sequence, TextIO

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_ANSI_CODES = {
    "bold": "1",
    "cyan": "36",
    "green": "32",
    "yellow": "33",
    "red": "31",
    "magenta": "35",
    "dim": "2",
}
_KIND_STYLES = {
    "info": ("cyan", "bold"),
    "success": ("green", "bold"),
    "warning": ("yellow", "bold"),
    "error": ("red", "bold"),
}


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


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
        if callable(isatty) and not isatty():
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
        stripped_widths = [len(_strip_ansi(line)) for line in lines]
        visible_width = max(stripped_widths, default=0)
        title_text = f" {title} "
        visible_width = max(visible_width, len(title_text))
        horizontal = "-" * (visible_width + 2)
        top = f"+{horizontal}+"
        if len(title_text) <= len(horizontal):
            top = f"+{title_text}{horizontal[len(title_text):]}+"
        bottom = f"+{horizontal}+"
        if accent:
            top = self.style(top, accent, "bold")
            bottom = self.style(bottom, accent, "bold")

        rendered = [top]
        for line, width in zip(lines, stripped_widths):
            rendered.append(f"| {line}{' ' * (visible_width - width)} |")
        rendered.append(bottom)
        return "\n".join(rendered)

    def definition_list(self, rows: Sequence[tuple[str, str]]) -> str:
        if not rows:
            return ""
        label_width = max(len(label) for label, _ in rows)
        lines: list[str] = []
        for label, description in rows:
            padded = f"{label:<{label_width}}"
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
            wrapped = textwrap.wrap(
                raw_line,
                width=width,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=False,
            )
            lines.extend(wrapped or [""])
        return lines
