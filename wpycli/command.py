from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from typing import Any

from .context import ArgsValidator, CommandContext, HookHandler, RunHandler
from .errors import BootstrapError, CLIError, UsageError
from .flags import Flag, FlagSet
from .output import Terminal
from .runtime import ConfigSettings, LoggingSettings, bootstrap_runtime

# Internal framework logger with NullHandler to prevent unconfigured root logging leaks.
INTERNAL_LOGGER_NAME = "wpycli._internal"
_logger = logging.getLogger(INTERNAL_LOGGER_NAME)
_logger.addHandler(logging.NullHandler())


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
        hidden: bool = False,
        deprecated: str | None = None,
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
        self.hidden = hidden
        self.deprecated = deprecated
        self.parent: Command | None = None
        self.commands: list[Command] = []
        self.flags = FlagSet()
        self.persistent_flags = FlagSet()
        self._config_settings: ConfigSettings | None = None
        self._logging_settings: LoggingSettings | None = None
        self._lineage_cache: tuple[Command, ...] | None = None
        self._full_path_cache: str | None = None

        if not self.use:
            raise ValueError("use must not be empty")

    @property
    def name(self) -> str:
        return self.use.split()[0]

    @property
    def full_path(self) -> str:
        if self._full_path_cache is not None:
            return self._full_path_cache
        self._full_path_cache = " ".join(command.name for command in self.lineage())
        return self._full_path_cache

    def lineage(self) -> tuple[Command, ...]:
        if self._lineage_cache is not None:
            return self._lineage_cache
        commands: list[Command] = []
        current: Command | None = self
        while current is not None:
            commands.append(current)
            current = current.parent
        self._lineage_cache = tuple(reversed(commands))
        return self._lineage_cache

    def root(self) -> Command:
        command = self
        while command.parent is not None:
            command = command.parent
        return command

    def matches(self, token: str) -> bool:
        return token == self.name or token in self.aliases

    def add_command(self, *commands: Command) -> Command:
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
            command._invalidate_lineage_cache()
            self.commands.append(command)
            taken |= names
        return self

    def _invalidate_lineage_cache(self) -> None:
        self._lineage_cache = None
        self._full_path_cache = None
        for command in self.commands:
            command._invalidate_lineage_cache()

    def find_subcommand(self, token: str) -> Command | None:
        for command in self.commands:
            if command.matches(token):
                return command
        return None

    def configure_runtime(
        self,
        *,
        config: ConfigSettings | None = None,
        logging: LoggingSettings | None = None,
    ) -> Command:
        self._config_settings = config
        self._logging_settings = logging
        return self

    def enable_no_color_flag(self) -> Command:
        """Register a persistent `--no-color` flag to disable colored terminal output."""
        self.add_persistent_bool_flag("no-color", help="Disable colored output")
        return self

    def add_completion_command(self) -> Command:
        """Register a hidden `completion <bash|zsh|fish>` subcommand to generate shell completion scripts."""
        from .args import exact_args
        from .completion import (
            generate_bash_completion,
            generate_fish_completion,
            generate_zsh_completion,
        )

        generators = {
            "bash": generate_bash_completion,
            "zsh": generate_zsh_completion,
            "fish": generate_fish_completion,
        }
        root = self.root()

        def _run_completion(context: CommandContext) -> int:
            shell = context.args[0]
            generator = generators.get(shell)
            if generator is None:
                raise UsageError(
                    f"unsupported shell {shell!r} (expected one of: bash, zsh, fish)"
                )
            print(generator(root))
            return 0

        completion_cmd = Command(
            use="completion <bash|zsh|fish>",
            short="Generate a shell completion script",
            run=_run_completion,
            hidden=True,
            args_validator=exact_args(1),
        )
        self.add_command(completion_cmd)
        return completion_cmd

    def add_flag(
        self,
        name: str,
        *,
        kind: str = "str",
        help: str = "",
        default: Any = None,
        shorthand: str | None = None,
        persistent: bool = False,
        required: bool = False,
        choices: Sequence[Any] | None = None,
        hidden: bool = False,
    ) -> Flag:
        target = self.persistent_flags if persistent else self.flags
        return target.create(
            name,
            kind=kind,
            help=help,
            default=default,
            shorthand=shorthand,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_string_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: str | None = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[str] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="str",
            help=help,
            default=default,
            shorthand=shorthand,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_int_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: int | None = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[int] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="int",
            help=help,
            default=default,
            shorthand=shorthand,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_float_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: float | None = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[float] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="float",
            help=help,
            default=default,
            shorthand=shorthand,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_bool_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: bool = False,
        shorthand: str | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="bool",
            help=help,
            default=default,
            shorthand=shorthand,
            hidden=hidden,
        )

    def add_count_flag(
        self,
        name: str,
        *,
        help: str = "",
        shorthand: str | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name, kind="count", help=help, default=0, shorthand=shorthand, hidden=hidden
        )

    def add_persistent_string_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: str | None = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[str] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="str",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_persistent_int_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: int | None = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[int] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="int",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_persistent_float_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: float | None = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[float] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="float",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
            required=required,
            choices=choices,
            hidden=hidden,
        )

    def add_persistent_bool_flag(
        self,
        name: str,
        *,
        help: str = "",
        default: bool = False,
        shorthand: str | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="bool",
            help=help,
            default=default,
            shorthand=shorthand,
            persistent=True,
            hidden=hidden,
        )

    def add_persistent_count_flag(
        self,
        name: str,
        *,
        help: str = "",
        shorthand: str | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add_flag(
            name,
            kind="count",
            help=help,
            default=0,
            shorthand=shorthand,
            persistent=True,
            hidden=hidden,
        )

    def execute(self, argv: Sequence[str] | None = None) -> int:
        from .help import help_text, usage_text
        from .parser import resolve_invocation

        argv_list = list(sys.argv[1:] if argv is None else argv)
        stdout_terminal = Terminal(stream=sys.stdout)
        stderr_terminal = Terminal(stream=sys.stderr)

        _logger.debug("Starting CLI execution with argv: %s", argv_list)
        try:
            resolved = resolve_invocation(self, argv_list)
            _logger.debug(
                "Resolved command: %s (args=%s, flags=%s, show_help=%s, show_version=%s)",
                resolved.command.full_path,
                resolved.args,
                resolved.flags,
                resolved.show_help,
                resolved.show_version,
            )

            if resolved.flags.get("no-color"):
                stdout_terminal = Terminal(stream=sys.stdout, force_color=False)
                stderr_terminal = Terminal(stream=sys.stderr, force_color=False)

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
            resolved.command._validate_flags(resolved.flags)
            if resolved.command.deprecated:
                print(
                    stderr_terminal.message(
                        "warning", "Deprecated", resolved.command.deprecated
                    ),
                    file=sys.stderr,
                )
            runtime_owner = resolved.command._runtime_owner()

            _logger.debug(
                "Bootstrapping runtime for owner: %s",
                runtime_owner.full_path if runtime_owner else "None",
            )
            try:
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
            except CLIError:
                raise
            except Exception as exc:
                # Map actionable bootstrap failures to BootstrapError for formatted CLI output.
                raise BootstrapError(str(exc), command=resolved.command) from exc
            context = CommandContext(
                command=resolved.command,
                argv=argv_list,
                args=resolved.args,
                flags=resolved.flags,
                config=runtime.config,
                logger=runtime.logger,
                terminal=stdout_terminal,
            )
            _logger.debug("Executing command logic...")
            return resolved.command._run(context)
        except CLIError as exc:
            _logger.debug("CLI usage error: %s", exc)
            if str(exc):
                print(
                    stderr_terminal.message("error", "Error", str(exc)), file=sys.stderr
                )
            if exc.command is not None:
                print(stderr_terminal.muted(usage_text(exc.command)), file=sys.stderr)
            return exc.exit_code
        except Exception as exc:
            # Hide traceback from terminal output while keeping full details in debug log.
            _logger.debug(
                "Unexpected system error occurred during execution", exc_info=True
            )
            print(
                stderr_terminal.message(
                    "error", "System Error", f"An unexpected error occurred: {exc}"
                ),
                file=sys.stderr,
            )
            return 1

    def usage_text(self) -> str:
        from .help import usage_text

        return usage_text(self)

    def help_text(self, terminal: Terminal | None = None) -> str:
        from .help import help_text

        return help_text(self, terminal)

    def _validate_args(self, args: list[str]) -> None:
        if self.args_validator is not None:
            self.args_validator(args)

    def _validate_flags(self, flag_values: dict[str, Any]) -> None:
        from .parser import flags_for_help

        for flag in flags_for_help(self.lineage()):
            value = flag_values.get(flag.name)
            if flag.required and value is None:
                raise UsageError(f"required flag --{flag.name} not set", command=self)
            if flag.choices and value is not None and value not in flag.choices:
                choices = ", ".join(repr(choice) for choice in flag.choices)
                raise UsageError(
                    f"invalid value for --{flag.name}: {value!r} (must be one of: {choices})",
                    command=self,
                )

    def _run(self, context: CommandContext) -> int:
        lineage = context.command.lineage()
        try:
            for command in lineage:
                if command.persistent_pre_run is not None:
                    _logger.debug(
                        "Executing persistent_pre_run for command: %s",
                        command.full_path,
                    )
                    command.persistent_pre_run(context)
            if context.command.pre_run is not None:
                _logger.debug(
                    "Executing pre_run for command: %s", context.command.full_path
                )
                context.command.pre_run(context)

            _logger.debug("Running handler for command: %s", context.command.full_path)
            result = (
                context.command.run(context) if context.command.run is not None else 0
            )

            if context.command.post_run is not None:
                _logger.debug(
                    "Executing post_run for command: %s", context.command.full_path
                )
                context.command.post_run(context)
            return 0 if result is None else int(result)
        finally:
            # Ensure persistent_post_run hooks always execute for proper cleanup.
            for command in reversed(lineage):
                if command.persistent_post_run is not None:
                    _logger.debug(
                        "Executing persistent_post_run for command: %s",
                        command.full_path,
                    )
                    command.persistent_post_run(context)

    def _runtime_owner(self) -> Command | None:
        for command in reversed(self.lineage()):
            if (
                command._config_settings is not None
                or command._logging_settings is not None
            ):
                return command
        return None
