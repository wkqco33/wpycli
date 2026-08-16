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

    # 패키지 이름 찾기 (main.py에서 추측하거나 현재 디렉토리의 유일한 디렉토리 찾기)
    # 일단 현재 디렉토리에 package_name/commands/root.py 가 있는지 확인
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
        # 1. 커맨드 파일 생성
        command_file.write_text(
            COMMAND_TEMPLATE.format(
                command_name=command_name,
                short_description=f"{command_name} command",
            )
        )
        print(f"Created {command_file.relative_to(target_dir)}")

        # 2. root.py에 등록 시도 (간단한 문자열 치환 방식)
        root_py = commands_dir / "root.py"
        content = root_py.read_text()

        import_line = (
            f"from .{command_name} import build_command as build_{command_name}_command"
        )
        register_line = f"    root.add_command(build_{command_name}_command())"

        if import_line not in content:
            # 파일 시작 부분(import 섹션)에 추가
            lines = content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("from wpycli"):
                    insert_idx = i + 1
                    break
            lines.insert(insert_idx, import_line)

            # return root 직전에 등록 추가
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
