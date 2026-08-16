from __future__ import annotations

from wpycli import Command, LoggingSettings

from .add import build_add_command
from .init import build_init_command


def build_cli() -> Command:
    root = Command(
        use="wpycli",
        short="wpycli management tool",
        long="A tool to initialize and manage wpycli projects, inspired by cobra-cli.",
    )
    root.add_persistent_string_flag("log-level", help="Override the logging level")
    root.add_persistent_string_flag("log-file", help="Write JSON logs to a file")

    root.configure_runtime(
        logging=LoggingSettings(
            logger_name="wpycli.cli",
            level_flag="log-level",
            log_file_flag="log-file",
        ),
    )

    root.add_command(
        build_init_command(),
        build_add_command(),
    )
    return root


def main() -> int:
    return build_cli().execute()


if __name__ == "__main__":
    raise SystemExit(main())
