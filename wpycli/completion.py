from __future__ import annotations

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


def generate_bash_completion(root: Command) -> str:
    """Generate a Bash completion script (requires Bash 4+)."""
    from .parser import flags_for_help

    lines = [
        f"# bash completion for {root.name}",
        f"_{root.name}_complete() {{",
        "    local cur cword",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        "    cword=$COMP_CWORD",
        "",
        "    declare -A _completions",
    ]
    for node in _walk(root):
        key = " ".join(_relative_path(node))
        children = [child.name for child in node.commands if not child.hidden]
        flags = [
            f"--{flag.name}"
            for flag in flags_for_help(node.lineage())
            if not flag.hidden
        ]
        options = " ".join(children + flags)
        lines.append(f'    _completions["{key}"]="{options}"')

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
            f"complete -F _{root.name}_complete {root.name}",
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
            lines.append(
                f'complete -c {root.name} -n "{condition}" -f -a "{child.name}"'
            )
        for flag in flags_for_help(node.lineage()):
            if flag.hidden:
                continue
            lines.append(f'complete -c {root.name} -n "{condition}" -l {flag.name}')
    return "\n".join(lines)
