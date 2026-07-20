from __future__ import annotations

MAIN_TEMPLATE = """from {package_name}.commands.root import build_cli


def main() -> int:
    return build_cli().execute()


if __name__ == "__main__":
    raise SystemExit(main())
"""

ROOT_COMMAND_TEMPLATE = """from __future__ import annotations

from wpycli import Command, CommandContext


def build_cli() -> Command:
    root = Command(
        use="{project_name}",
        short="{short_description}",
        long="{long_description}",
    )

    # root.add_command(...)
    return root
"""

CONFIG_TEMPLATE = """server:
  host: 127.0.0.1
  port: 8080

logging:
  level: INFO
"""

COMMAND_TEMPLATE = """from __future__ import annotations

from wpycli import Command, CommandContext


def _run_{command_name}(context: CommandContext) -> int:
    print(f"Executing {command_name}...")
    return 0


def build_command() -> Command:
    cmd = Command(
        use="{command_name}",
        short="{short_description}",
        run=_run_{command_name},
    )
    return cmd
"""
