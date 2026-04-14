from __future__ import annotations

import json

from wpycli import Command, CommandContext, ConfigSettings, LoggingSettings


def _log_command(context: CommandContext) -> None:
    if context.logger is not None:
        context.logger.info("executing %s", context.command.full_path)


def _run_serve(context: CommandContext) -> int:
    host = context.config.get("server.host", "127.0.0.1") if context.config is not None else "127.0.0.1"
    port = context.config.get("server.port", 8080) if context.config is not None else 8080
    if context.logger is not None:
        context.logger.info("resolved server target %s:%s", host, port)
    print(context.terminal.message("success", "Serve", f"serving on {host}:{port}"))
    return 0


def _run_config(context: CommandContext) -> int:
    payload = context.config.as_dict() if context.config is not None else {}
    rendered = context.terminal.pretty_json(json.dumps(payload, indent=2, sort_keys=True))
    print(context.terminal.panel("Merged configuration", rendered, accent="magenta"))
    return 0


def _run_echo(context: CommandContext) -> int:
    message = " ".join(context.args)
    if context.flags.get("upper"):
        message = message.upper()
    print(context.terminal.message("info", "Echo", message))
    return 0


def build_cli() -> Command:
    root = Command(
        use="wpycli",
        short="Cobra-inspired CLI toolkit for Python",
        long="A small Python CLI toolkit modeled after Cobra's command tree and execution flow.",
        version="0.1.0",
        persistent_pre_run=_log_command,
    )
    root.add_persistent_string_flag("config", shorthand="c", help="Path to a YAML configuration file")
    root.add_persistent_string_flag("dotenv", help="Path to a .env file")
    root.add_persistent_string_flag("log-level", help="Override the logging level")
    root.add_persistent_string_flag("log-file", help="Write JSON logs to a file")
    root.add_persistent_string_flag("error-log-file", help="Write ERROR logs to a dedicated file")

    root.configure_runtime(
        config=ConfigSettings(
            defaults={
                "server": {
                    "host": "127.0.0.1",
                    "port": 8080,
                },
                "logging": {
                    "level": "INFO",
                },
            },
            env_prefix="WPYCLI",
            file_flag="config",
            dotenv_flag="dotenv",
        ),
        logging=LoggingSettings(
            logger_name="wpycli",
            level_flag="log-level",
            log_file_flag="log-file",
            error_file_flag="error-log-file",
        ),
    )

    serve = Command(use="serve", short="Print the resolved server target", run=_run_serve)
    show_config = Command(use="config", short="Print the merged configuration", run=_run_config)
    echo = Command(use="echo", short="Echo positional arguments", run=_run_echo)
    echo.add_bool_flag("upper", shorthand="u", help="Uppercase the echoed output")

    root.add_command(serve, show_config, echo)
    return root


def main() -> int:
    return build_cli().execute()


if __name__ == "__main__":
    raise SystemExit(main())
