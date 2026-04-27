from __future__ import annotations

from pathlib import Path

from wpycli import Command, CommandContext
from .templates import MAIN_TEMPLATE, ROOT_COMMAND_TEMPLATE


def _run_init(context: CommandContext) -> int:
    project_name = context.args[0] if context.args else Path.cwd().name
    target_dir = Path.cwd()

    # 패키지 이름은 소문자와 언더스코어만 허용하는 관례를 따름
    package_name = project_name.lower().replace("-", "_")

    print(f"Initializing {project_name} in {target_dir}...")

    # 1. commands 디렉토리 생성
    commands_dir = target_dir / package_name / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    (target_dir / package_name / "__init__.py").touch()
    (commands_dir / "__init__.py").touch()

    # 2. root.py 생성
    root_py = commands_dir / "root.py"
    if not root_py.exists():
        root_py.write_text(
            ROOT_COMMAND_TEMPLATE.format(
                project_name=project_name,
                short_description=f"{project_name} CLI tool",
                long_description=f"{project_name} is a CLI tool built with wpycli.",
            )
        )
        print(f"  Created {root_py.relative_to(target_dir)}")

    # 3. main.py 생성
    main_py = target_dir / "main.py"
    if not main_py.exists():
        main_py.write_text(MAIN_TEMPLATE.format(package_name=package_name))
        print(f"  Created {main_py.relative_to(target_dir)}")

    print(f"\nSuccessfully initialized {project_name}!")
    return 0


def build_init_command() -> Command:
    cmd = Command(
        use="init [name]",
        short="Initialize a new wpycli project",
        run=_run_init,
    )
    return cmd
