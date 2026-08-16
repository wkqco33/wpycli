from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from wpycli import Command, exact_args, max_args, min_args, range_args


class RequiredAndChoicesFlagTests(unittest.TestCase):
    def _build(self) -> Command:
        root = Command(use="app", run=lambda ctx: 0)
        root.add_string_flag("name", required=True)
        root.add_string_flag("env", choices=["dev", "prod"], default="dev")
        return root

    def test_missing_required_flag_is_usage_error(self) -> None:
        root = self._build()
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = root.execute([])

        self.assertEqual(exit_code, 2)
        self.assertIn("required flag --name not set", stderr.getvalue())

    def test_invalid_choice_is_usage_error(self) -> None:
        root = self._build()
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = root.execute(["--name", "x", "--env", "staging"])

        self.assertEqual(exit_code, 2)
        self.assertIn("must be one of", stderr.getvalue())

    def test_valid_required_and_choice_flags_run_successfully(self) -> None:
        root = self._build()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            exit_code = root.execute(["--name", "x", "--env", "prod"])

        self.assertEqual(exit_code, 0)

    def test_invalid_default_choice_rejected_at_registration(self) -> None:
        root = Command(use="app")
        with self.assertRaises(ValueError):
            root.add_string_flag("env", choices=["dev", "prod"], default="staging")


class CountFlagTests(unittest.TestCase):
    def test_repeated_shorthand_cluster_accumulates(self) -> None:
        captured: dict[str, object] = {}
        root = Command(
            use="app", run=lambda ctx: captured.update(v=ctx.flags["verbose"])
        )
        root.add_count_flag("verbose", shorthand="v")

        with redirect_stdout(io.StringIO()):
            root.execute(["-vvv"])

        self.assertEqual(captured["v"], 3)

    def test_repeated_long_flag_accumulates(self) -> None:
        captured: dict[str, object] = {}
        root = Command(
            use="app", run=lambda ctx: captured.update(v=ctx.flags["verbose"])
        )
        root.add_count_flag("verbose")

        with redirect_stdout(io.StringIO()):
            root.execute(["--verbose", "--verbose"])

        self.assertEqual(captured["v"], 2)

    def test_default_count_is_zero(self) -> None:
        captured: dict[str, object] = {}
        root = Command(
            use="app", run=lambda ctx: captured.update(v=ctx.flags["verbose"])
        )
        root.add_count_flag("verbose", shorthand="v")

        with redirect_stdout(io.StringIO()):
            root.execute([])

        self.assertEqual(captured["v"], 0)


class TypoSuggestionTests(unittest.TestCase):
    def test_unknown_command_suggests_close_match(self) -> None:
        root = Command(use="app")
        root.add_command(Command(use="serve", run=lambda ctx: 0))

        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            root.execute(["srve"])

        self.assertIn("Did you mean this?", stderr.getvalue())
        self.assertIn("serve", stderr.getvalue())

    def test_unknown_flag_suggests_close_match(self) -> None:
        root = Command(use="app", run=lambda ctx: 0)
        root.add_bool_flag("verbose")

        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            root.execute(["--verboze"])

        self.assertIn("Did you mean this?", stderr.getvalue())
        self.assertIn("--verbose", stderr.getvalue())


class HiddenAndDeprecatedTests(unittest.TestCase):
    def test_hidden_command_excluded_from_help(self) -> None:
        root = Command(use="app")
        root.add_command(Command(use="visible", short="visible cmd", run=lambda ctx: 0))
        root.add_command(
            Command(use="secret", short="hidden cmd", run=lambda ctx: 0, hidden=True)
        )

        text = root.help_text()
        self.assertIn("visible", text)
        self.assertNotIn("secret", text)

    def test_hidden_flag_excluded_from_help(self) -> None:
        root = Command(use="app", run=lambda ctx: 0)
        root.add_string_flag("public", help="public flag")
        root.add_string_flag("internal", help="internal flag", hidden=True)

        text = root.help_text()
        self.assertIn("--public", text)
        self.assertNotIn("--internal", text)

    def test_deprecated_command_shows_warning_and_help_marker(self) -> None:
        root = Command(use="app")
        old = Command(
            use="old", short="legacy", run=lambda ctx: 0, deprecated="use 'new' instead"
        )
        root.add_command(old)

        self.assertIn("(deprecated)", root.help_text())

        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = root.execute(["old"])

        self.assertEqual(exit_code, 0)
        self.assertIn("use 'new' instead", stderr.getvalue())


class ArgsHelpersTests(unittest.TestCase):
    def _run(self, validator, argv: list[str]) -> tuple[int, str]:
        root = Command(use="app", run=lambda ctx: 0, args_validator=validator)
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = root.execute(argv)
        return exit_code, stderr.getvalue()

    def test_exact_args(self) -> None:
        validator = exact_args(2)
        self.assertEqual(self._run(validator, ["a", "b"])[0], 0)
        code, err = self._run(validator, ["a"])
        self.assertEqual(code, 2)
        self.assertIn("accepts 2 arg(s)", err)

    def test_min_args(self) -> None:
        validator = min_args(2)
        self.assertEqual(self._run(validator, ["a", "b", "c"])[0], 0)
        code, err = self._run(validator, ["a"])
        self.assertEqual(code, 2)
        self.assertIn("at least 2", err)

    def test_max_args(self) -> None:
        validator = max_args(1)
        self.assertEqual(self._run(validator, ["a"])[0], 0)
        code, err = self._run(validator, ["a", "b"])
        self.assertEqual(code, 2)
        self.assertIn("at most 1", err)

    def test_range_args(self) -> None:
        validator = range_args(1, 2)
        self.assertEqual(self._run(validator, ["a"])[0], 0)
        self.assertEqual(self._run(validator, ["a", "b"])[0], 0)
        code, err = self._run(validator, [])
        self.assertEqual(code, 2)
        self.assertIn("between 1 and 2", err)


if __name__ == "__main__":
    unittest.main()
