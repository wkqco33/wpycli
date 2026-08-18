from __future__ import annotations

import re
import shlex
from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .command import Command


def _walk(command: Command) -> Iterator[Command]:
    yield command
    for child in command.commands:
        if child.hidden:
            continue
        yield from _walk(child)


def _relative_path(command: Command) -> tuple[str, ...]:
    return tuple(command.full_path.split()[1:])


def _completion_function_name(root: Command) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", root.name)
    return f"_{name}"


def _escape_bash_double_quoted(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
    )


def generate_bash_completion(root: Command) -> str:
    """Generate a Bash completion script (requires Bash 4+)."""
    from .parser import flags_for_help

    function_name = _completion_function_name(root)
    lines = [
        f"# bash completion for {root.name}",
        f"{function_name}_complete() {{",
        "    local cur cword",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        "    cword=$COMP_CWORD",
        "",
        "    declare -A _completions",
    ]
    for node in _walk(root):
        key = " ".join(_relative_path(node))
        children = [
            name
            for child in node.commands
            if not child.hidden
            for name in (child.name, *child.aliases)
        ]
        flags = []
        for flag in flags_for_help(node.lineage()):
            if flag.hidden:
                continue
            flags.append(f"--{flag.name}")
            if flag.shorthand:
                flags.append(f"-{flag.shorthand}")
        options = " ".join(children + flags)
        lines.append(
            f'    _completions["{_escape_bash_double_quoted(key)}"]="{_escape_bash_double_quoted(options)}"'
        )

    lines.extend(
        [
            "",
            '    local path=""',
            "    local i word",
            "    for ((i = 1; i < cword; i++)); do",
            '        word="${COMP_WORDS[i]}"',
            '        [[ "$word" == -* ]] && continue',
            '        if [[ -n "$path" ]]; then path="$path $word"; else path="$word"; fi',
            "    done",
            "",
            '    COMPREPLY=($(compgen -W "${_completions[$path]}" -- "$cur"))',
            "}",
            f"complete -F {function_name}_complete {shlex.quote(root.name)}",
            "",
        ]
    )
    return "\n".join(lines)


def generate_zsh_completion(root: Command) -> str:
    """Generate a Zsh completion script using bashcompinit."""
    return (
        f"#compdef {root.name}\n"
        "autoload -U +X bashcompinit && bashcompinit\n\n"
        f"{generate_bash_completion(root)}"
    )


def generate_fish_completion(root: Command) -> str:
    """Generate a Fish completion script."""
    from .parser import flags_for_help

    lines = [f"# fish completion for {root.name}"]
    for node in _walk(root):
        path = _relative_path(node)
        condition = (
            "__fish_use_subcommand"
            if not path
            else f"__fish_seen_subcommand_from {' '.join(path)}"
        )
        for child in node.commands:
            if child.hidden:
                continue
            for name in (child.name, *child.aliases):
                lines.append(f'complete -c {root.name} -n "{condition}" -f -a "{name}"')
        for flag in flags_for_help(node.lineage()):
            if flag.hidden:
                continue
            lines.append(f'complete -c {root.name} -n "{condition}" -l {flag.name}')
            if flag.shorthand:
                lines.append(
                    f'complete -c {root.name} -n "{condition}" -s {flag.shorthand}'
                )
    return "\n".join(lines)
