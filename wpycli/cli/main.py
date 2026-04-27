from __future__ import annotations

from wpycli import Command
from .init import build_init_command
from .add import build_add_command


def build_cli() -> Command:
    root = Command(
        use="wpycli",
        short="wpycli management tool",
        long="A tool to initialize and manage wpycli projects, inspired by cobra-cli.",
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
