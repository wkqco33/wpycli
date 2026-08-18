from __future__ import annotations

import difflib
import logging
from collections.abc import Iterable
from dataclasses import dataclass

from .command import INTERNAL_LOGGER_NAME, Command
from .errors import UnknownCommandError, UnknownFlagError, UsageError
from .flags import Flag, FlagValue

_logger = logging.getLogger(INTERNAL_LOGGER_NAME)


def _suggest(token: str, candidates: Iterable[str]) -> str | None:
    matches = difflib.get_close_matches(token, list(candidates), n=1, cutoff=0.6)
    return matches[0] if matches else None


def _command_names(command: Command) -> list[str]:
    names: list[str] = []
    for child in command.commands:
        names.append(child.name)
        names.extend(child.aliases)
    return names


@dataclass(slots=True)
class ResolvedInvocation:
    command: Command
    lineage: tuple[Command, ...]
    args: list[str]
    flags: dict[str, FlagValue]
    show_help: bool = False
    show_version: bool = False


def resolve_invocation(command: Command, argv: list[str]) -> ResolvedInvocation:
    _logger.debug("Resolving invocation: argv=%s", argv)
    current = command
    args: list[str] = []
    parsed_flags: dict[str, FlagValue] = {}
    index = 0
    flag_maps = _flag_maps(current.lineage())

    while index < len(argv):
        token = argv[index]

        if token == "--":
            args.extend(argv[index + 1 :])
            break

        if token == "help":
            target = _resolve_help_target(current, argv[index + 1 :])
            return _build_invocation(target, parsed_flags, show_help=True)

        if (
            token == "version"
            and current is command
            and command.version
            and command.find_subcommand("version") is None
        ):
            if index != len(argv) - 1:
                raise UsageError(
                    "version does not accept additional arguments", command=command
                )
            return _build_invocation(command, parsed_flags, show_version=True)

        if token.startswith("-") and token != "-":
            next_index, outcome = _consume_flag(
                argv, index, current, parsed_flags, flag_maps, command.root()
            )
            if outcome == "help":
                return _build_invocation(current, parsed_flags, show_help=True)
            if outcome == "version":
                return _build_invocation(command, parsed_flags, show_version=True)
            index = next_index
            continue

        child = current.find_subcommand(token) if not args else None
        if child is not None:
            current = child
            flag_maps = _flag_maps(current.lineage())
            index += 1
            continue

        if current.commands and current.run is None and not args:
            raise UnknownCommandError(
                token,
                command=current,
                suggestion=_suggest(token, _command_names(current)),
            )

        args.append(token)
        index += 1

    if current.run is None and current.commands and not args:
        return _build_invocation(current, parsed_flags, show_help=True)
    return _build_invocation(current, parsed_flags, args=args)


def _consume_flag(
    argv: list[str],
    index: int,
    current: Command,
    parsed_flags: dict[str, FlagValue],
    flag_maps: tuple[dict[str, Flag], dict[str, Flag]],
    root_command: Command,
) -> tuple[int, str | None]:
    long_flags, short_flags = flag_maps
    token = argv[index]

    if token in {"-h", "--help"}:
        return index + 1, "help"
    if token == "--version" and root_command.version:
        return index + 1, "version"

    if token.startswith("--"):
        name, has_value, value = token[2:].partition("=")
        flag = long_flags.get(name)
        if flag is None:
            suggestion = _suggest(name, long_flags.keys())
            raise UnknownFlagError(
                token,
                command=current,
                suggestion=f"--{suggestion}" if suggestion else None,
            )
        if flag.takes_value:
            raw_value = (
                value if has_value else _next_flag_value(argv, index, flag, current)
            )
            parsed_flags[flag.name] = _convert_flag_value(flag, raw_value, current)
            return (index + 1) if has_value else (index + 2), None
        if has_value:
            parsed_flags[flag.name] = _convert_flag_value(flag, value, current)
        else:
            _mark_flag_present(flag, parsed_flags)
        return index + 1, None

    cluster = token[1:]
    offset = 0
    while offset < len(cluster):
        shorthand = cluster[offset]
        if shorthand == "h":
            return index + 1, "help"
        flag = short_flags.get(shorthand)
        if flag is None:
            raise UnknownFlagError(f"-{shorthand}", command=current)
        if flag.takes_value:
            attached = cluster[offset + 1 :]
            if attached:
                parsed_flags[flag.name] = _convert_flag_value(flag, attached, current)
                return index + 1, None
            raw_value = _next_flag_value(argv, index, flag, current)
            parsed_flags[flag.name] = _convert_flag_value(flag, raw_value, current)
            return index + 2, None
        _mark_flag_present(flag, parsed_flags)
        offset += 1

    return index + 1, None


def _mark_flag_present(flag: Flag, parsed_flags: dict[str, FlagValue]) -> None:
    if flag.kind == "count":
        current = parsed_flags.get(flag.name, 0)
        if not isinstance(current, int):
            raise TypeError(f"count flag --{flag.name} has a non-integer value")
        parsed_flags[flag.name] = current + 1
    else:
        parsed_flags[flag.name] = True


def _next_flag_value(argv: list[str], index: int, flag: Flag, command: Command) -> str:
    if index + 1 >= len(argv):
        raise UsageError(f"flag --{flag.name} requires a value", command=command)
    return argv[index + 1]


def _convert_flag_value(flag: Flag, raw_value: str, command: Command) -> FlagValue:
    try:
        return flag.convert(raw_value)
    except ValueError as exc:
        raise UsageError(
            f"invalid value for --{flag.name}: {raw_value!r}", command=command
        ) from exc


def _resolve_help_target(start: Command, tokens: list[str]) -> Command:
    target = start
    for token in tokens:
        if token.startswith("-"):
            raise UsageError("help does not accept flags", command=target)
        child = target.find_subcommand(token)
        if child is None:
            raise UnknownCommandError(
                token,
                command=target,
                suggestion=_suggest(token, _command_names(target)),
            )
        target = child
    return target


def _build_invocation(
    command: Command,
    parsed_flags: dict[str, FlagValue],
    *,
    args: list[str] | None = None,
    show_help: bool = False,
    show_version: bool = False,
) -> ResolvedInvocation:
    lineage = command.lineage()
    flag_values = _default_flag_values(lineage)
    flag_values.update(parsed_flags)
    return ResolvedInvocation(
        command=command,
        lineage=lineage,
        args=args or [],
        flags=flag_values,
        show_help=show_help,
        show_version=show_version,
    )


def _default_flag_values(lineage: tuple[Command, ...]) -> dict[str, FlagValue]:
    defaults: dict[str, FlagValue] = {}
    for flag in flags_for_help(lineage):
        defaults.setdefault(flag.name, flag.default)
    return defaults


def _flag_maps(lineage: tuple[Command, ...]) -> tuple[dict[str, Flag], dict[str, Flag]]:
    long_flags: dict[str, Flag] = {}
    short_flags: dict[str, Flag] = {}
    for flag in flags_for_help(lineage):
        long_flags[flag.name] = flag
        if flag.shorthand:
            short_flags[flag.shorthand] = flag
    return long_flags, short_flags


def flags_for_help(lineage: tuple[Command, ...]) -> tuple[Flag, ...]:
    flags: list[Flag] = []
    for command in lineage:
        flags.extend(command.persistent_flags)
    flags.extend(lineage[-1].flags)

    names: set[str] = set()
    shorthands: set[str] = set()
    for flag in flags:
        if flag.name in names:
            raise UsageError(
                f"duplicate flag name in command lineage: --{flag.name}",
                command=lineage[-1],
            )
        if flag.shorthand is not None and flag.shorthand in shorthands:
            raise UsageError(
                f"duplicate flag shorthand in command lineage: -{flag.shorthand}",
                command=lineage[-1],
            )
        names.add(flag.name)
        if flag.shorthand is not None:
            shorthands.add(flag.shorthand)
    return tuple(flags)


def inherited_persistent_flags(lineage: tuple[Command, ...]) -> tuple[Flag, ...]:
    return tuple(f for cmd in lineage[:-1] for f in cmd.persistent_flags)
