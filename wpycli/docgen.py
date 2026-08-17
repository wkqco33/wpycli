from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .flags import Flag

if TYPE_CHECKING:
    from .command import Command


def _flag_line(flag: Flag) -> str:
    names = f"`--{flag.name}`"
    if flag.shorthand:
        names += f", `-{flag.shorthand}`"
    return f"- {names}: {flag.help}".rstrip(": ")


def generate_markdown_docs(root: Command, out_dir: str | Path) -> list[Path]:
    """Recursively generate Markdown documentation files for a command tree."""
    from .help import usage_text
    from .parser import inherited_persistent_flags

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def _file_name(command: Command) -> str:
        return f"{command.full_path.replace(' ', '_')}.md"

    def _walk(command: Command) -> None:
        lines = [f"# {command.full_path}", "", "```", usage_text(command), "```", ""]

        if command.deprecated:
            lines.extend([f"> **Deprecated:** {command.deprecated}", ""])
        if command.long:
            lines.extend([command.long, ""])
        elif command.short:
            lines.extend([command.short, ""])

        local_flags = [
            flag
            for flag in (*command.persistent_flags, *command.flags)
            if not flag.hidden
        ]
        if local_flags:
            lines.append("## Flags")
            lines.append("")
            lines.extend(
                _flag_line(flag) for flag in sorted(local_flags, key=lambda f: f.name)
            )
            lines.append("")

        inherited = [
            flag
            for flag in inherited_persistent_flags(command.lineage())
            if not flag.hidden
        ]
        if inherited:
            lines.append("## Inherited Flags")
            lines.append("")
            lines.extend(
                _flag_line(flag) for flag in sorted(inherited, key=lambda f: f.name)
            )
            lines.append("")

        visible_children = [child for child in command.commands if not child.hidden]
        if visible_children:
            lines.append("## Subcommands")
            lines.append("")
            for child in visible_children:
                summary = f": {child.short}" if child.short else ""
                lines.append(f"- [{child.full_path}]({_file_name(child)}){summary}")
            lines.append("")

        file_path = out_path / _file_name(command)
        file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        written.append(file_path)

        for child in visible_children:
            _walk(child)

    _walk(root)
    return written
