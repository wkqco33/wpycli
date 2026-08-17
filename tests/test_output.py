from __future__ import annotations

import unicodedata
import unittest

from wpycli import Terminal
from wpycli.utils import split_cjk_and_words, strip_ansi, visual_width


class TerminalTests(unittest.TestCase):
    def test_panel_uses_ascii_frame_without_color_by_default(self) -> None:
        terminal = Terminal()
        rendered = terminal.panel("Demo", ["hello", "world"])

        self.assertIn("+ Demo ", rendered)
        self.assertIn("| hello", rendered)
        self.assertIn("| world", rendered)
        self.assertNotIn("\x1b[", rendered)

    def test_definition_list_aligns_labels(self) -> None:
        terminal = Terminal()
        rendered = terminal.definition_list(
            [
                ("--config PATH", "Path to config file"),
                ("--verbose", "Enable verbose output"),
            ]
        )

        self.assertIn("--config PATH", rendered)
        self.assertIn("Path to config file", rendered)
        self.assertIn("--verbose", rendered)

    def test_panel_with_korean_text_aligns_correctly(self) -> None:
        terminal = Terminal()
        rendered = terminal.panel("타이틀", ["한글", "hello"])

        lines = rendered.splitlines()
        from wpycli.utils import visual_width

        body_lines = [
            line if line.startswith("|") and line.endswith("|") else ""
            for line in lines
        ]
        body_lines = [line for line in body_lines if line]
        self.assertEqual(len(body_lines), 2)

        width1 = visual_width(body_lines[0])
        width2 = visual_width(body_lines[1])
        self.assertEqual(width1, width2)

    def test_definition_list_with_korean_labels_aligns_correctly(self) -> None:
        terminal = Terminal()
        rendered = terminal.definition_list(
            [
                ("가나다", "Korean label"),
                ("abc", "English label"),
            ]
        )

        clean_rendered = strip_ansi(rendered)
        lines = clean_rendered.splitlines()

        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("  가나다  Korean"))
        self.assertTrue(lines[1].startswith("  abc     English"))

    def test_visual_width_is_normalization_independent(self) -> None:
        composed = "설정"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(visual_width(composed), visual_width(decomposed))

    def test_panel_border_stays_aligned_with_nfd_korean_title(self) -> None:
        terminal = Terminal()
        composed = "설정"
        decomposed = unicodedata.normalize("NFD", composed)

        rendered = terminal.panel(decomposed, ["a"])
        lines = rendered.splitlines()
        top, body, bottom = lines[0], lines[1], lines[2]

        self.assertEqual(visual_width(top), visual_width(bottom))
        self.assertEqual(visual_width(top), visual_width(body))

    def test_split_cjk_and_words_handles_decomposed_hangul(self) -> None:
        decomposed = unicodedata.normalize("NFD", "한글ABC테스트")
        self.assertEqual(
            split_cjk_and_words(decomposed), ["한", "글", "ABC", "테", "스", "트"]
        )

    def test_style_supports_extended_color_palette(self) -> None:
        terminal = Terminal(force_color=True)

        self.assertEqual(terminal.style("x", "blue"), "\x1b[34mx\x1b[0m")
        self.assertEqual(terminal.style("x", "white"), "\x1b[37mx\x1b[0m")
        self.assertEqual(terminal.style("x", "black"), "\x1b[30mx\x1b[0m")
        self.assertEqual(terminal.style("x", "bright_red"), "\x1b[91mx\x1b[0m")

    def test_style_supports_text_decorations(self) -> None:
        terminal = Terminal(force_color=True)

        self.assertEqual(terminal.style("x", "underline"), "\x1b[4mx\x1b[0m")
        self.assertEqual(terminal.style("x", "italic"), "\x1b[3mx\x1b[0m")
        self.assertEqual(terminal.style("x", "strikethrough"), "\x1b[9mx\x1b[0m")

    def test_panel_accent_accepts_any_registered_color(self) -> None:
        terminal = Terminal(force_color=True)
        rendered = terminal.panel("t", ["body"], accent="blue")
        self.assertIn("\x1b[34;1m", rendered)


if __name__ == "__main__":
    unittest.main()
