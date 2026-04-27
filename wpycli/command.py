from __future__ import annotations

import sys
from typing import Any, Sequence

from .context import ArgsValidator, CommandContext, HookHandler, RunHandler
from .errors import CLIError, UsageError
from .flags import Flag, FlagSet
from .output import Terminal
from .runtime import ConfigSettings, LoggingSettings, bootstrap_runtime


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
        taken = {
            name for child in self.commands for name in (child.name, *child.aliases)
        }
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
        return target.create(
            name, kind=kind, help=help, default=default, shorthand=shorthand
        )

    def add_string_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: str | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name, kind="str", help=help, default=default, shorthand=shorthand
        )

    def add_int_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: int | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name, kind="int", help=help, default=default, shorthand=shorthand
        )

    def add_float_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: float | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name, kind="float", help=help, default=default, shorthand=shorthand
        )

    def add_bool_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: bool = False,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name, kind="bool", help=help, default=default, shorthand=shorthand
        )

    def add_persistent_string_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: str | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="str",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
        )

    def add_persistent_int_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: int | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="int",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
        )

    def add_persistent_float_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: float | None = None,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="float",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
        )

    def add_persistent_bool_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: bool = False,
        shorthand: str | None = None,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="bool",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
        )

    def execute(self, argv: Sequence[str] | None = None) -> int:
        from .help import help_text, usage_text
        from .parser import resolve_invocation

        argv_list = list(sys.argv[1:] if argv is None else argv)
        stdout_terminal = Terminal(stream=sys.stdout)
        stderr_terminal = Terminal(stream=sys.stderr)
        try:
            resolved = resolve_invocation(self, argv_list)
            if resolved.show_help:
                print(help_text(resolved.command, stdout_terminal))
                return 0
            if resolved.show_version:
                version = self.root().version
                if not version:
                    raise UsageError("version is not configured", command=self.root())
                print(version)
                return 0
            if resolved.command.run is None:
                raise UsageError(
                    f"{resolved.command.full_path} is not runnable",
                    command=resolved.command,
                )

            resolved.command._validate_args(resolved.args)
            runtime_owner = resolved.command._runtime_owner()
            runtime = bootstrap_runtime(
                command_name=resolved.command.full_path,
                flag_values=resolved.flags,
                config_settings=runtime_owner._config_settings
                if runtime_owner
                else None,
                logging_settings=runtime_owner._logging_settings
                if runtime_owner
                else None,
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
                print(
                    stderr_terminal.message("error", "Error", str(exc)), file=sys.stderr
                )
            if exc.command is not None:
                print(stderr_terminal.muted(usage_text(exc.command)), file=sys.stderr)
            return exc.exit_code

    def usage_text(self) -> str:
        from .help import usage_text

        return usage_text(self)

    def help_text(self, terminal: Terminal | None = None) -> str:
        from .help import help_text

        return help_text(self, terminal)

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
            if (
                command._config_settings is not None
                or command._logging_settings is not None
            ):
                return command
        return None
