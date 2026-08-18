from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from wpycli import Command, UnknownCommandError, UnknownFlagError, UsageError
from wpycli.cli.main import build_cli
from wpycli.flags import Flag, FlagSet
from wpycli.parser import resolve_invocation
from wpycli.utils import split_cjk_and_words, strip_ansi, visual_width, visual_wrap


class UtilityEdgeTests(unittest.TestCase):
    def test_ansi_sequences_are_removed_before_width_measurement(self) -> None:
        text = "\x1b[1;31m赤\x1b[0m A"
        self.assertEqual(strip_ansi(text), "赤 A")
        self.assertEqual(visual_width(text), 4)

    def test_split_preserves_ascii_runs_and_splits_ambiguous_characters(self) -> None:
        self.assertEqual(
            split_cjk_and_words("ab·한글cd"), ["ab", "·", "한", "글", "cd"]
        )

    def test_wrap_handles_overlong_cjk_run_and_overflowing_whitespace(self) -> None:
        self.assertEqual(visual_wrap("你好世界", 4), ["你好", "世界"])
        self.assertEqual(visual_wrap("one two", 3), ["one", " ", "two"])
        self.assertEqual(visual_wrap("abcdef", 3), ["abc", "def"])
        with self.assertRaisesRegex(ValueError, "width must be positive"):
            visual_wrap("text", 0)

    def test_empty_and_combining_text_have_stable_normalized_width(self) -> None:
        self.assertEqual(visual_width(""), 0)
        self.assertEqual(visual_width("e\u0301"), visual_width("é"))


class FlagEdgeTests(unittest.TestCase):
    def test_flag_conversion_and_metadata(self) -> None:
        self.assertEqual(Flag("count", kind="count").convert("3"), 3)
        self.assertEqual(Flag("enabled", kind="bool").convert(" YES "), True)
        self.assertFalse(Flag("enabled", kind="bool").convert("off"))
        self.assertEqual(Flag("ratio", kind="float").convert("1.25"), 1.25)
        self.assertFalse(Flag("enabled", kind="bool").takes_value)
        self.assertEqual(Flag("count", kind="count").metavar, "COUNT")

    def test_invalid_flag_definition_and_conversion_failures(self) -> None:
        with self.assertRaisesRegex(ValueError, "shell-safe long name"):
            Flag("--bad")
        with self.assertRaisesRegex(ValueError, "shell-safe single character"):
            Flag("name", shorthand="vv")
        with self.assertRaisesRegex(ValueError, "shell-safe long name"):
            Flag("bad name")

    def test_command_names_and_aliases_are_shell_safe(self) -> None:
        with self.assertRaisesRegex(ValueError, "shell-safe token"):
            Command(use="bad/name")
        with self.assertRaisesRegex(ValueError, "shell-safe tokens"):
            Command(use="app", aliases=("bad alias",))
        with self.assertRaisesRegex(ValueError, "unsupported flag kind"):
            Flag("name", kind="path")
        with self.assertRaisesRegex(ValueError, "invalid boolean"):
            Flag("enabled", kind="bool").convert("maybe")

    def test_flag_set_lookup_defaults_and_duplicates(self) -> None:
        flags = FlagSet()
        created = flags.create("port", kind="int", default=8080, shorthand="p")
        self.assertIs(flags.get("port"), created)
        self.assertIs(flags.get_short("p"), created)
        self.assertEqual(flags.defaults(), {"port": 8080})
        self.assertTrue(flags)
        with self.assertRaisesRegex(ValueError, "duplicate flag name"):
            flags.create("port")
        with self.assertRaisesRegex(ValueError, "duplicate flag shorthand"):
            flags.create("other", shorthand="p")


class ParserMalformedInputTests(unittest.TestCase):
    def _command(self) -> Command:
        command = Command(use="app", run=lambda context: 0)
        command.add_int_flag("port", shorthand="p")
        command.add_bool_flag("verbose", shorthand="v")
        command.add_string_flag("mode", choices=["safe", "fast"])
        return command

    def test_missing_value_is_a_usage_error(self) -> None:
        with self.assertRaisesRegex(UsageError, "requires a value"):
            resolve_invocation(self._command(), ["--port"])

    def test_invalid_value_and_unknown_flag_are_usage_errors(self) -> None:
        with self.assertRaisesRegex(UsageError, "invalid value for --port"):
            resolve_invocation(self._command(), ["--port", "not-an-int"])
        with self.assertRaisesRegex(UnknownFlagError, "unknown flag '--por'"):
            resolve_invocation(self._command(), ["--por"])

    def test_short_attached_value_and_double_dash_are_parsed(self) -> None:
        invocation = resolve_invocation(
            self._command(), ["-p8080", "--", "--verbose", "literal"]
        )
        self.assertEqual(invocation.flags["port"], 8080)
        self.assertEqual(invocation.args, ["--verbose", "literal"])

    def test_unknown_subcommand_and_help_flags_are_rejected(self) -> None:
        command = Command(use="app")
        command.add_command(Command(use="serve", run=lambda context: 0))
        with self.assertRaisesRegex(UnknownCommandError, "unknown command 'ser"):
            resolve_invocation(command, ["ser"])
        with self.assertRaisesRegex(UsageError, "help does not accept flags"):
            resolve_invocation(command, ["help", "--verbose"])

    def test_parser_sees_flags_added_after_an_initial_resolution(self) -> None:
        command = Command(use="app", run=lambda context: 0)
        resolve_invocation(command, [])
        command.add_bool_flag("verbose")

        invocation = resolve_invocation(command, ["--verbose"])

        self.assertTrue(invocation.flags["verbose"])

    def test_inherited_flag_collisions_are_rejected(self) -> None:
        root = Command(use="app")
        root.add_persistent_bool_flag("verbose", shorthand="v")
        child = Command(use="serve", run=lambda context: 0)
        child.add_bool_flag("verbose", shorthand="q")
        root.add_command(child)

        with self.assertRaisesRegex(UsageError, "duplicate flag name"):
            resolve_invocation(root, ["serve"])


class ManagementCLIQualityTests(unittest.TestCase):
    def test_build_cli_constructs_management_commands_and_dispatches_init(self) -> None:
        root = build_cli()
        self.assertEqual(root.name, "wpycli")
        self.assertEqual({command.name for command in root.commands}, {"init", "add"})
        self.assertEqual(
            root.persistent_flags.defaults(), {"log-level": None, "log-file": None}
        )

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                stdout = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                    exit_code = root.execute(["init", "demo-project"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue(
                Path(temporary, "demo_project", "commands", "root.py").exists()
            )
            self.assertIn("Successfully initialized demo-project", stdout.getvalue())

    def test_management_command_reports_malformed_add_invocation(self) -> None:
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = build_cli().execute(["add"])
        self.assertEqual(exit_code, 2)
        self.assertIn("command name is required", stderr.getvalue())

    def test_management_command_rejects_path_traversal_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            escaped_name = f"outside_{Path(temporary).name}"
            original_cwd = os.getcwd()
            try:
                os.chdir(temporary)
                stderr = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                    exit_code = build_cli().execute(["init", f"../{escaped_name}"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 2)
        self.assertIn("invalid project name", stderr.getvalue())
        self.assertFalse(Path(temporary).parent.joinpath(escaped_name).exists())

    def test_management_command_rejects_extra_arguments(self) -> None:
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = build_cli().execute(["add", "serve", "extra"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Usage: wpycli add", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
