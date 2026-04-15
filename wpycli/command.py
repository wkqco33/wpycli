from __future__ import annotations

from dataclasses import dataclass
import logging
import sys
from typing import Any, Callable, Sequence

from .flags import Flag, FlagSet
from .output import Terminal
from .runtime import ConfigSettings, LoggingSettings, bootstrap_runtime

RunHandler = Callable[["CommandContext"], int | None]
HookHandler = Callable[["CommandContext"], None]
ArgsValidator = Callable[[list[str]], None]


class CLIError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2, command: Command | None = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.command = command


class UsageError(CLIError):
    pass


class UnknownCommandError(UsageError):
    def __init__(self, token: str, *, command: Command) -> None:
        super().__init__(f"unknown command {token!r} for {command.full_path}", command=command)


class UnknownFlagError(UsageError):
    def __init__(self, token: str, *, command: Command) -> None:
        super().__init__(f"unknown flag {token!r}", command=command)


@dataclass(slots=True)
class CommandContext:
    command: "Command"
    argv: list[str]
    args: list[str]
    flags: dict[str, Any]
    config: Any = None
    logger: logging.Logger | None = None
    terminal: Terminal | None = None


@dataclass(slots=True)
class _ResolvedInvocation:
    command: "Command"
    lineage: tuple["Command", ...]
    args: list[str]
    flags: dict[str, Any]
    show_help: bool = False
    show_version: bool = False


class Command:
    def __init__(
        self,
        *,
        use: str,
        short: str = "",
        long: str = "",
        aliases: Sequence[str] = (),
        run: RunHandler | None = None,
        pre_run: HookHandler | None = None,
        post_run: HookHandler | None = None,
        persistent_pre_run: HookHandler | None = None,
        persistent_post_run: HookHandler | None = None,
        args_validator: ArgsValidator | None = None,
        version: str | None = None,
    ) -> None:
        self.use = use.strip()
        self.short = short.strip()
        self.long = long.strip()
        self.aliases = tuple(aliases)
        self.run = run
        self.pre_run = pre_run
        self.post_run = post_run
        self.persistent_pre_run = persistent_pre_run
        self.persistent_post_run = persistent_post_run
        self.args_validator = args_validator
        self.version = version
        self.parent: Command | None = None
        self.commands: list[Command] = []
        self.flags = FlagSet()
        self.persistent_flags = FlagSet()
        self._config_settings: ConfigSettings | None = None
        self._logging_settings: LoggingSettings | None = None

        if not self.use:
            raise ValueError("use must not be empty")

    @property
    def name(self) -> str:
        return self.use.split()[0]

    @property
    def full_path(self) -> str:
        return " ".join(command.name for command in self.lineage())

    def lineage(self) -> tuple["Command", ...]:
        commands: list[Command] = []
        current: Command | None = self
        while current is not None:
            commands.append(current)
            current = current.parent
        return tuple(reversed(commands))

    def root(self) -> "Command":
        command = self
        while command.parent is not None:
            command = command.parent
        return command

    def matches(self, token: str) -> bool:
        return token == self.name or token in self.aliases

    def add_command(self, *commands: "Command") -> "Command":
        taken = {name for child in self.commands for name in (child.name, *child.aliases)}
        for command in commands:
            if command.parent is not None:
                raise ValueError(f"command {command.name!r} already has a parent")
            names = {command.name, *command.aliases}
            if taken & names:
                duplicate = next(iter(taken & names))
                raise ValueError(f"duplicate command name or alias: {duplicate}")
            command.parent = self
            self.commands.append(command)
            taken |= names
        return self

    def find_subcommand(self, token: str) -> "Command | None":
        for command in self.commands:
            if command.matches(token):
                return command
        return None

    def configure_runtime(
        self,
        *,
        config: ConfigSettings | None = None,
        logging: LoggingSettings | None = None,
    ) -> "Command":
        self._config_settings = config
        self._logging_settings = logging
        return self

    def add_flag(
        self,
        name: str,
        *,
        kind: str = "str",
        help: str = "",
        default: Any = None,
        shorthand: str | None = None,
        persistent: bool = False,
    ) -> Flag:
        target = self.persistent_flags if persistent else self.flags
        return target.create(name, kind=kind, help=help, default=default, shorthand=shorthand)

    def add_string_flag(self, name: str, *, help: str = "", default: str | None = None, shorthand: str | None = None) -> Flag:
        return self.add_flag(name, kind="str", help=help, default=default, shorthand=shorthand)

    def add_int_flag(self, name: str, *, help: str = "", default: int | None = None, shorthand: str | None = None) -> Flag:
        return self.add_flag(name, kind="int", help=help, default=default, shorthand=shorthand)

    def add_float_flag(self, name: str, *, help: str = "", default: float | None = None, shorthand: str | None = None) -> Flag:
        return self.add_flag(name, kind="float", help=help, default=default, shorthand=shorthand)

    def add_bool_flag(self, name: str, *, help: str = "", default: bool = False, shorthand: str | None = None) -> Flag:
        return self.add_flag(name, kind="bool", help=help, default=default, shorthand=shorthand)

    def add_persistent_string_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: str | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(name, kind="str", help=help, default=default, shorthand=shorthand, persistent=True)

    def add_persistent_int_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: int | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(name, kind="int", help=help, default=default, shorthand=shorthand, persistent=True)

    def add_persistent_float_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: float | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(name, kind="float", help=help, default=default, shorthand=shorthand, persistent=True)

    def add_persistent_bool_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: bool = False,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(name, kind="bool", help=help, default=default, shorthand=shorthand, persistent=True)

    def execute(self, argv: Sequence[str] | None = None) -> int:
        argv_list = list(sys.argv[1:] if argv is None else argv)
        stdout_terminal = Terminal(stream=sys.stdout)
        stderr_terminal = Terminal(stream=sys.stderr)
        try:
            resolved = self._resolve(argv_list)
            if resolved.show_help:
                print(resolved.command.help_text(stdout_terminal))
                return 0
            if resolved.show_version:
                version = self.root().version
                if not version:
                    raise UsageError("version is not configured", command=self.root())
                print(version)
                return 0
            if resolved.command.run is None:
                raise UsageError(f"{resolved.command.full_path} is not runnable", command=resolved.command)

            resolved.command._validate_args(resolved.args)
            runtime_owner = resolved.command._runtime_owner()
            runtime = bootstrap_runtime(
                command_name=resolved.command.full_path,
                flag_values=resolved.flags,
                config_settings=runtime_owner._config_settings if runtime_owner else None,
                logging_settings=runtime_owner._logging_settings if runtime_owner else None,
            )
            context = CommandContext(
                command=resolved.command,
                argv=argv_list,
                args=resolved.args,
                flags=resolved.flags,
                config=runtime.config,
                logger=runtime.logger,
                terminal=stdout_terminal,
            )
            return resolved.command._run(context)
        except CLIError as exc:
            if str(exc):
                print(stderr_terminal.message("error", "Error", str(exc)), file=sys.stderr)
            if exc.command is not None:
                print(stderr_terminal.muted(exc.command.usage_text()), file=sys.stderr)
            return exc.exit_code

    def usage_text(self) -> str:
        parts = [self.full_path]
        if self.commands:
            parts.append("[command]")
        if self._flags_for_help(self.lineage()):
            parts.append("[flags]")
        parts.append("[args]")
        return f"Usage: {' '.join(parts)}"

    def help_text(self, terminal: Terminal | None = None) -> str:
        terminal = terminal or Terminal()
        lineage = self.lineage()
        summary_lines = [terminal.muted(self.usage_text())]
        if self.long:
            summary_lines.extend(["", self.long])
        elif self.short:
            summary_lines.extend(["", self.short])

        lines = [terminal.panel(self.full_path, summary_lines)]

        if self.commands:
            rows: list[tuple[str, str]] = []
            for child in self.commands:
                names = child.name
                if child.aliases:
                    names = f"{names} [{', '.join(child.aliases)}]"
                summary = child.short or child.long or ""
                rows.append((names, summary))
            lines.extend(["", terminal.section("Commands"), terminal.definition_list(rows)])

        local_flags = tuple(self.persistent_flags) + tuple(self.flags)
        inherited_flags = self._inherited_persistent_flags(lineage)
        if local_flags:
            lines.extend(["", terminal.section("Flags"), terminal.definition_list(self._format_flags(local_flags))])
        if inherited_flags:
            lines.extend(["", terminal.section("Inherited Flags"), terminal.definition_list(self._format_flags(inherited_flags))])

        builtin_lines = [("-h, --help", "Show help for this command")]
        if self.root().version:
            builtin_lines.append(("--version", "Show the application version"))
        lines.extend(["", terminal.section("Built-in Flags"), terminal.definition_list(builtin_lines)])
        return "\n".join(lines)

    def _validate_args(self, args: list[str]) -> None:
        if self.args_validator is not None:
            self.args_validator(args)

    def _run(self, context: CommandContext) -> int:
        lineage = context.command.lineage()
        for command in lineage:
            if command.persistent_pre_run is not None:
                command.persistent_pre_run(context)
        if context.command.pre_run is not None:
            context.command.pre_run(context)

        result = context.command.run(context) if context.command.run is not None else 0

        if context.command.post_run is not None:
            context.command.post_run(context)
        for command in reversed(lineage):
            if command.persistent_post_run is not None:
                command.persistent_post_run(context)
        return 0 if result is None else int(result)

    def _runtime_owner(self) -> "Command | None":
        for command in reversed(self.lineage()):
            if command._config_settings is not None or command._logging_settings is not None:
                return command
        return None

    def _resolve(self, argv: list[str]) -> _ResolvedInvocation:
        current = self
        args: list[str] = []
        parsed_flags: dict[str, Any] = {}
        index = 0
        flag_maps = self._flag_maps(current.lineage())

        while index < len(argv):
            token = argv[index]

            if token == "--":
                args.extend(argv[index + 1 :])
                break

            if token == "help":
                target = self._resolve_help_target(current, argv[index + 1 :])
                return self._build_invocation(target, parsed_flags, show_help=True)

            if token == "version" and current is self and self.version and self.find_subcommand("version") is None:
                if index != len(argv) - 1:
                    raise UsageError("version does not accept additional arguments", command=self)
                return self._build_invocation(self, parsed_flags, show_version=True)

            if token.startswith("-") and token != "-":
                next_index, outcome = self._consume_flag(argv, index, current, parsed_flags, flag_maps)
                if outcome == "help":
                    return self._build_invocation(current, parsed_flags, show_help=True)
                if outcome == "version":
                    return self._build_invocation(self, parsed_flags, show_version=True)
                index = next_index
                continue

            child = current.find_subcommand(token) if not args else None
            if child is not None:
                current = child
                flag_maps = self._flag_maps(current.lineage())
                index += 1
                continue

            if current.commands and current.run is None and not args:
                raise UnknownCommandError(token, command=current)

            args.append(token)
            index += 1

        if current.run is None and current.commands and not args:
            return self._build_invocation(current, parsed_flags, show_help=True)
        return self._build_invocation(current, parsed_flags, args=args)

    def _consume_flag(
        self,
        argv: list[str],
        index: int,
        current: "Command",
        parsed_flags: dict[str, Any],
        flag_maps: tuple[dict[str, "Flag"], dict[str, "Flag"]],
    ) -> tuple[int, str | None]:
        long_flags, short_flags = flag_maps
        token = argv[index]

        if token in {"-h", "--help"}:
            return index + 1, "help"
        if token == "--version" and self.root().version:
            return index + 1, "version"

        if token.startswith("--"):
            name, has_value, value = token[2:].partition("=")
            flag = long_flags.get(name)
            if flag is None:
                raise UnknownFlagError(token, command=current)
            if flag.takes_value:
                raw_value = value if has_value else self._next_flag_value(argv, index, flag, current)
                parsed_flags[flag.name] = self._convert_flag_value(flag, raw_value, current)
                return (index + 1) if has_value else (index + 2), None
            if has_value:
                parsed_flags[flag.name] = self._convert_flag_value(flag, value, current)
            else:
                parsed_flags[flag.name] = True
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
                    parsed_flags[flag.name] = self._convert_flag_value(flag, attached, current)
                    return index + 1, None
                raw_value = self._next_flag_value(argv, index, flag, current)
                parsed_flags[flag.name] = self._convert_flag_value(flag, raw_value, current)
                return index + 2, None
            parsed_flags[flag.name] = True
            offset += 1

        return index + 1, None

    def _next_flag_value(self, argv: list[str], index: int, flag: Flag, command: "Command") -> str:
        if index + 1 >= len(argv):
            raise UsageError(f"flag --{flag.name} requires a value", command=command)
        return argv[index + 1]

    def _convert_flag_value(self, flag: Flag, raw_value: str, command: "Command") -> Any:
        try:
            return flag.convert(raw_value)
        except ValueError as exc:
            raise UsageError(f"invalid value for --{flag.name}: {raw_value!r}", command=command) from exc

    def _resolve_help_target(self, start: "Command", tokens: list[str]) -> "Command":
        target = start
        for token in tokens:
            if token.startswith("-"):
                raise UsageError("help does not accept flags", command=target)
            child = target.find_subcommand(token)
            if child is None:
                raise UnknownCommandError(token, command=target)
            target = child
        return target

    def _build_invocation(
        self,
        command: "Command",
        parsed_flags: dict[str, Any],
        *,
        args: list[str] | None = None,
        show_help: bool = False,
        show_version: bool = False,
    ) -> _ResolvedInvocation:
        lineage = command.lineage()
        flag_values = self._default_flag_values(lineage)
        flag_values.update(parsed_flags)
        return _ResolvedInvocation(
            command=command,
            lineage=lineage,
            args=args or [],
            flags=flag_values,
            show_help=show_help,
            show_version=show_version,
        )

    def _default_flag_values(self, lineage: tuple["Command", ...]) -> dict[str, Any]:
        defaults: dict[str, Any] = {}
        for flag in self._flags_for_help(lineage):
            defaults.setdefault(flag.name, flag.default)
        return defaults

    def _flag_maps(self, lineage: tuple["Command", ...]) -> tuple[dict[str, Flag], dict[str, Flag]]:
        long_flags: dict[str, Flag] = {}
        short_flags: dict[str, Flag] = {}
        for flag in self._flags_for_help(lineage):
            long_flags[flag.name] = flag
            if flag.shorthand:
                short_flags[flag.shorthand] = flag
        return long_flags, short_flags

    def _flags_for_help(self, lineage: tuple["Command", ...]) -> tuple[Flag, ...]:
        flags: list[Flag] = []
        for command in lineage:
            flags.extend(command.persistent_flags)
        flags.extend(lineage[-1].flags)
        return tuple(flags)

    def _inherited_persistent_flags(self, lineage: tuple["Command", ...]) -> tuple[Flag, ...]:
        return tuple(f for cmd in lineage[:-1] for f in cmd.persistent_flags)

    def _format_flags(self, flags: tuple[Flag, ...]) -> list[tuple[str, str]]:
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
