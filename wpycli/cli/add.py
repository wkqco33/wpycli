from __future__ import annotations

from pathlib import Path

from wpycli import Command, CommandContext, UsageError

from .files import atomic_write_files
from .naming import normalize_identifier
from .templates import COMMAND_TEMPLATE


def _find_package_name(target_dir: Path) -> str:
    try:
        candidates = sorted(
            p.name
            for p in target_dir.iterdir()
            if p.is_dir() and (p / "commands" / "root.py").is_file()
        )
    except OSError as exc:
        raise UsageError(f"Could not inspect project directory: {exc}") from exc

    if not candidates:
        raise UsageError(
            "Could not find wpycli project structure. Please run 'wpycli init' first."
        )
    if len(candidates) > 1:
        names = ", ".join(candidates)
        raise UsageError(
            f"Found multiple wpycli projects in the current directory: {names}"
        )
    return candidates[0]


def _updated_root_content(
    content: str, *, import_line: str, register_line: str, root_py: Path
) -> str:
    lines = content.splitlines()
    if import_line not in content:
        import_indices = [
            index
            for index, line in enumerate(lines)
            if line.startswith("from ") or line.startswith("import ")
        ]
        insert_index = import_indices[-1] + 1 if import_indices else 0
        lines.insert(insert_index, import_line)

    if register_line not in content:
        return_indices = [
            index for index, line in enumerate(lines) if line.strip() == "return root"
        ]
        if not return_indices:
            raise UsageError(
                f"Could not update {root_py.name}: expected a `return root` line"
            )
        lines.insert(return_indices[-1], register_line)

    updated = "\n".join(lines) + "\n"
    try:
        compile(updated, str(root_py), "exec")
    except SyntaxError as exc:
        raise UsageError(f"Could not update {root_py.name}: {exc}") from exc
    return updated


def _require_command_name(args: list[str]) -> None:
    if not args:
        raise UsageError("command name is required")
    if len(args) > 1:
        raise UsageError("accepts exactly one command name")


def _run_add(context: CommandContext) -> int:
    command_name = normalize_identifier(
        context.args[0],
        label="command name",
        reserved=frozenset({"root", "__init__"}),
    )
    target_dir = Path.cwd()
    stream = context.terminal.stream if context.terminal is not None else None

    package_name = _find_package_name(target_dir)
    commands_dir = target_dir / package_name / "commands"
    command_file = commands_dir / f"{command_name}.py"

    if command_file.exists() and not context.flags.get("force"):
        raise UsageError(
            f"command {command_name!r} already exists (use --force to overwrite)."
        )

    root_py = commands_dir / "root.py"
    import_line = (
        f"from .{command_name} import build_command as build_{command_name}_command"
    )
    register_line = f"    root.add_command(build_{command_name}_command())"

    try:
        content = root_py.read_text(encoding="utf-8")
        updated_root = _updated_root_content(
            content,
            import_line=import_line,
            register_line=register_line,
            root_py=root_py,
        )
        command_content = COMMAND_TEMPLATE.format(
            command_name=command_name,
            short_description=f"{command_name} command",
        )
        files_to_write = {command_file: command_content}
        if updated_root != content:
            files_to_write[root_py] = updated_root
        atomic_write_files(files_to_write)
    except (OSError, UnicodeError) as exc:
        raise UsageError(f"Could not add command {command_name!r}: {exc}") from exc

    print(f"Created {command_file.relative_to(target_dir)}", file=stream)
    if updated_root != content:
        print(
            f"Updated {root_py.relative_to(target_dir)} to register {command_name}",
            file=stream,
        )

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
