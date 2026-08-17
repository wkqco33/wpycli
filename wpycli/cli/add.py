from __future__ import annotations

from pathlib import Path

from wpycli import Command, CommandContext, UsageError

from .templates import COMMAND_TEMPLATE


def _require_command_name(args: list[str]) -> None:
    if not args:
        raise UsageError("command name is required")


def _run_add(context: CommandContext) -> int:
    command_name = context.args[0].lower().replace("-", "_")
    target_dir = Path.cwd()

    # Locate project package root by finding directory containing commands/root.py
    package_name = None
    for p in target_dir.iterdir():
        if p.is_dir() and (p / "commands" / "root.py").exists():
            package_name = p.name
            break

    if not package_name:
        raise UsageError(
            "Could not find wpycli project structure. Please run 'wpycli init' first."
        )

    commands_dir = target_dir / package_name / "commands"
    command_file = commands_dir / f"{command_name}.py"

    if command_file.exists() and not context.flags.get("force"):
        raise UsageError(
            f"command {command_name!r} already exists (use --force to overwrite)."
        )

    try:
        # 1. Create command file
        command_file.write_text(
            COMMAND_TEMPLATE.format(
                command_name=command_name,
                short_description=f"{command_name} command",
            )
        )
        print(f"Created {command_file.relative_to(target_dir)}")

        # 2. Register command in root.py
        root_py = commands_dir / "root.py"
        content = root_py.read_text()

        import_line = (
            f"from .{command_name} import build_command as build_{command_name}_command"
        )
        register_line = f"    root.add_command(build_{command_name}_command())"

        if import_line not in content:
            # Add import statement
            lines = content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("from wpycli"):
                    insert_idx = i + 1
                    break
            lines.insert(insert_idx, import_line)

            # Add command registration before returning root
            for i, line in enumerate(lines):
                if "return root" in line:
                    lines.insert(i, register_line)
                    break

            root_py.write_text("\n".join(lines) + "\n")
            print(
                f"Updated {root_py.relative_to(target_dir)} to register {command_name}"
            )
    except OSError as exc:
        raise UsageError(f"Could not add command {command_name!r}: {exc}") from exc

    return 0


def build_add_command() -> Command:
    cmd = Command(
        use="add [name]",
        short="Add a new command to the project",
        run=_run_add,
        args_validator=_require_command_name,
    )
    cmd.add_bool_flag(
        "force", shorthand="f", help="Overwrite the command file if it already exists"
    )
    return cmd
