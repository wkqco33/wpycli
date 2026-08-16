from __future__ import annotations

from pathlib import Path

from wpycli import Command, CommandContext, UsageError

from .templates import CONFIG_TEMPLATE, MAIN_TEMPLATE, ROOT_COMMAND_TEMPLATE


def _run_init(context: CommandContext) -> int:
    project_name = context.args[0] if context.args else Path.cwd().name
    target_dir = Path.cwd()
    force = bool(context.flags.get("force"))
    with_config = bool(context.flags.get("with-config"))

    # 패키지 이름은 소문자와 언더스코어만 허용하는 관례를 따름
    package_name = project_name.lower().replace("-", "_")

    print(f"Initializing {project_name} in {target_dir}...")

    try:
        # 1. commands 디렉토리 생성
        commands_dir = target_dir / package_name / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / package_name / "__init__.py").touch()
        (commands_dir / "__init__.py").touch()

        # 2. root.py 생성
        root_py = commands_dir / "root.py"
        if force or not root_py.exists():
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
        if force or not main_py.exists():
            main_py.write_text(MAIN_TEMPLATE.format(package_name=package_name))
            print(f"  Created {main_py.relative_to(target_dir)}")

        # 4. (선택) config.yaml 생성
        if with_config:
            config_path = target_dir / "config.yaml"
            if force or not config_path.exists():
                config_path.write_text(CONFIG_TEMPLATE)
                print(f"  Created {config_path.relative_to(target_dir)}")
    except OSError as exc:
        raise UsageError(f"Could not initialize {project_name!r}: {exc}") from exc

    print(f"\nSuccessfully initialized {project_name}!")
    return 0


def build_init_command() -> Command:
    cmd = Command(
        use="init [name]",
        short="Initialize a new wpycli project",
        run=_run_init,
    )
    cmd.add_bool_flag("force", shorthand="f", help="Overwrite existing files")
    cmd.add_bool_flag("with-config", help="Also generate a starter config.yaml")
    return cmd
