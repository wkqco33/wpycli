from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from wpycli.cli.add import build_add_command
from wpycli.cli.init import build_init_command


class _InTempDir:
    def __init__(self) -> None:
        self._cwd: str = ""
        self._tmp: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Path:
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        return Path.cwd()

    def __exit__(self, *exc_info: object) -> None:
        os.chdir(self._cwd)
        if self._tmp is not None:
            self._tmp.cleanup()


class AddCommandTests(unittest.TestCase):
    def test_missing_name_is_a_usage_error(self) -> None:
        with _InTempDir():
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = build_add_command().execute([])

        self.assertEqual(exit_code, 2)
        self.assertIn("command name is required", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_outside_project_is_a_usage_error(self) -> None:
        with _InTempDir():
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = build_add_command().execute(["serve"])

        self.assertEqual(exit_code, 2)
        self.assertIn("wpycli init", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_add_after_init_creates_and_registers_command(self) -> None:
        with _InTempDir() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                init_exit = build_init_command().execute(["demo"])
                add_exit = build_add_command().execute(["serve"])

            self.assertEqual(init_exit, 0)
            self.assertEqual(add_exit, 0)
            command_file = tmp / "demo" / "commands" / "serve.py"
            self.assertTrue(command_file.exists())
            self.assertIn("file=context.stdout", command_file.read_text())
            root_contents = (tmp / "demo" / "commands" / "root.py").read_text()
            self.assertIn("build_serve_command", root_contents)

    def test_duplicate_command_is_a_usage_error(self) -> None:
        with _InTempDir():
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                build_init_command().execute(["demo"])
                build_add_command().execute(["serve"])

            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = build_add_command().execute(["serve"])

        self.assertEqual(exit_code, 2)
        self.assertIn("already exists", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_duplicate_command_with_force_overwrites(self) -> None:
        with _InTempDir() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                build_init_command().execute(["demo"])
                build_add_command().execute(["serve"])
                exit_code = build_add_command().execute(["serve", "--force"])

            self.assertEqual(exit_code, 0)
            command_file = tmp / "demo" / "commands" / "serve.py"
            self.assertTrue(command_file.exists())
            # Re-registering an already-imported command must not duplicate
            # the import/registration lines in root.py.
            root_contents = (tmp / "demo" / "commands" / "root.py").read_text()
            self.assertEqual(root_contents.count("build_serve_command"), 2)


class InitCommandTests(unittest.TestCase):
    def test_rerun_without_force_leaves_existing_files_untouched(self) -> None:
        with _InTempDir() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                build_init_command().execute(["demo"])
                root_py = tmp / "demo" / "commands" / "root.py"
                root_py.write_text(root_py.read_text() + "\n# custom edit\n")
                build_init_command().execute(["demo"])

            self.assertIn("# custom edit", root_py.read_text())

    def test_rerun_with_force_overwrites_existing_files(self) -> None:
        with _InTempDir() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                build_init_command().execute(["demo"])
                root_py = tmp / "demo" / "commands" / "root.py"
                root_py.write_text(root_py.read_text() + "\n# custom edit\n")
                build_init_command().execute(["demo", "--force"])

            self.assertNotIn("# custom edit", root_py.read_text())

    def test_with_config_generates_loadable_yaml(self) -> None:
        with _InTempDir() as tmp:
            with redirect_stdout(io.StringIO()):
                exit_code = build_init_command().execute(["demo", "--with-config"])

            self.assertEqual(exit_code, 0)
            config_path = tmp / "config.yaml"
            self.assertTrue(config_path.exists())

            from wconfig import load_config

            cfg = load_config(files=(str(config_path),))
            self.assertEqual(cfg.get("server.port"), 8080)

    def test_without_with_config_flag_no_config_file_is_created(self) -> None:
        with _InTempDir() as tmp:
            with redirect_stdout(io.StringIO()):
                build_init_command().execute(["demo"])

            self.assertFalse((tmp / "config.yaml").exists())


if __name__ == "__main__":
    unittest.main()
