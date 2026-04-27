from __future__ import annotations

from typing import TYPE_CHECKING

from .output import Terminal
from .parser import flags_for_help, inherited_persistent_flags

if TYPE_CHECKING:
    from .command import Command
    from .flags import Flag


def usage_text(command: Command) -> str:
    parts = [command.full_path]
    if command.commands:
        parts.append("[command]")
    if flags_for_help(command.lineage()):
        parts.append("[flags]")
    parts.append("[args]")
    return f"Usage: {' '.join(parts)}"


def help_text(command: Command, terminal: Terminal | None = None) -> str:
    terminal = terminal or Terminal()
    lineage = command.lineage()
    summary_lines = [terminal.muted(usage_text(command))]
    if command.long:
        summary_lines.extend(["", command.long])
    elif command.short:
        summary_lines.extend(["", command.short])

    lines = [terminal.panel(command.full_path, summary_lines)]

    if command.commands:
        rows: list[tuple[str, str]] = []
        for child in command.commands:
            names = child.name
            if child.aliases:
                names = f"{names} [{', '.join(child.aliases)}]"
            summary = child.short or child.long or ""
            rows.append((names, summary))
        lines.extend(
            ["", terminal.section("Commands"), terminal.definition_list(rows)]
        )

    local_flags = tuple(command.persistent_flags) + tuple(command.flags)
    inherited_flags = inherited_persistent_flags(lineage)

    if local_flags:
        lines.extend(
            [
                "",
                terminal.section("Flags"),
                terminal.definition_list(_format_flags(local_flags)),
            ]
        )
    if inherited_flags:
        lines.extend(
            [
                "",
                terminal.section("Inherited Flags"),
                terminal.definition_list(_format_flags(inherited_flags)),
            ]
        )

    builtin_lines = [("-h, --help", "Show help for this command")]
    if command.root().version:
        builtin_lines.append(("--version", "Show the application version"))
    lines.extend(
        [
            "",
            terminal.section("Built-in Flags"),
            terminal.definition_list(builtin_lines),
        ]
    )
    return "\n".join(lines)


def _format_flags(flags: tuple[Flag, ...]) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for flag in sorted(flags, key=lambda item: item.name):
        names = [f"--{flag.name}"]
        if flag.shorthand:
            names.insert(0, f"-{flag.shorthand}")
        label = ", ".join(names)
        if flag.takes_value:
            label = f"{label} {flag.metavar}"
        description = flag.help
        if flag.default not in {None, False}:
            description = f"{description} (default: {flag.default})".strip()
        lines.append((label, description))
    return lines
