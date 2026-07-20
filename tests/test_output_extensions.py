from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from wpycli import Command, ProgressBar, Spinner, Terminal
from wpycli.utils import visual_width


class TableTests(unittest.TestCase):
    def test_columns_align_across_rows_with_korean_content(self) -> None:
        terminal = Terminal(force_color=False)
        rendered = terminal.table(
            ["이름", "상태", "설명"],
            [
                ["serve", "실행중", "서버를 시작합니다"],
                ["config", "정지됨", "설정을 표시"],
                ["a", "ok", "x"],
            ],
        )
        lines = rendered.splitlines()
        col0_width = max(visual_width(h) for h in ["이름", "serve", "config", "a"])
        boundary = col0_width + 2

        for line in lines:
            # Walk to the boundary offset; every row's 2nd column must start
            # at the exact same visual column regardless of Hangul width.
            acc = 0
            idx = 0
            for ch in line:
                if acc >= boundary:
                    break
                acc += visual_width(ch)
                idx += 1
            self.assertEqual(acc, boundary, msg=f"misaligned row: {line!r}")

    def test_header_separator_matches_header_width(self) -> None:
        terminal = Terminal(force_color=False)
        rendered = terminal.table(["a", "b"], [["1", "2"]])
        header, separator = rendered.splitlines()[:2]
        self.assertEqual(visual_width(header), visual_width(separator))


class ConfirmPromptTests(unittest.TestCase):
    def test_confirm_returns_default_on_empty_input(self) -> None:
        terminal = Terminal()
        with patch("builtins.input", return_value=""):
            self.assertTrue(terminal.confirm("proceed?", default=True))
            self.assertFalse(terminal.confirm("proceed?", default=False))

    def test_confirm_parses_yes_no(self) -> None:
        terminal = Terminal()
        with patch("builtins.input", return_value="y"):
            self.assertTrue(terminal.confirm("proceed?"))
        with patch("builtins.input", return_value="no"):
            self.assertFalse(terminal.confirm("proceed?", default=True))

    def test_prompt_delegates_to_input(self) -> None:
        terminal = Terminal()
        with patch("builtins.input", return_value="hello") as mock_input:
            result = terminal.prompt("name: ")
        self.assertEqual(result, "hello")
        mock_input.assert_called_once_with("name: ")

    def test_prompt_secret_uses_getpass(self) -> None:
        terminal = Terminal()
        with patch("getpass.getpass", return_value="secret") as mock_getpass:
            result = terminal.prompt("password: ", secret=True)
        self.assertEqual(result, "secret")
        mock_getpass.assert_called_once_with("password: ")


class SpinnerTests(unittest.TestCase):
    def test_non_tty_prints_single_line_and_ticks_are_noop(self) -> None:
        buf = io.StringIO()
        with Spinner("loading", stream=buf) as spinner:
            spinner.tick()
            spinner.tick()

        self.assertEqual(buf.getvalue(), "loading...\n")

    def test_tty_ticks_render_frames_and_clear_on_exit(self) -> None:
        class FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        buf = FakeTTY()
        with Spinner("한글 로딩", stream=buf) as spinner:
            spinner.tick()

        output = buf.getvalue()
        self.assertIn("\r", output)
        self.assertTrue(output.endswith("\r"))


class ProgressBarTests(unittest.TestCase):
    def test_non_tty_prints_milestones_and_reaches_100(self) -> None:
        buf = io.StringIO()
        with ProgressBar(10, stream=buf) as bar:
            for _ in range(10):
                bar.update(1)

        lines = buf.getvalue().splitlines()
        self.assertIn("[##############################] 100%", lines[-1])

    def test_updates_never_exceed_total(self) -> None:
        buf = io.StringIO()
        with ProgressBar(5, stream=buf) as bar:
            bar.update(100)
        self.assertEqual(bar.current, 5)


class NoColorFlagTests(unittest.TestCase):
    def test_enable_no_color_flag_strips_ansi_when_passed(self) -> None:
        root = Command(
            use="app", run=lambda ctx: print(ctx.terminal.style("x", "red"))
        )
        root.enable_no_color_flag()

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            root.execute(["--no-color"])

        self.assertNotIn("\x1b[", stdout.getvalue())

    def test_without_flag_registration_no_color_is_just_an_unknown_flag(self) -> None:
        root = Command(use="app", run=lambda ctx: 0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = root.execute(["--no-color"])
        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
