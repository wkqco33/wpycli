from __future__ import annotations

import unittest

from wpycli import Terminal


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
        
        body_lines = [line if line.startswith("|") and line.endswith("|") else "" for line in lines]
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
        
        from wpycli.utils import strip_ansi
        clean_rendered = strip_ansi(rendered)
        lines = clean_rendered.splitlines()
        
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("  가나다  Korean"))
        self.assertTrue(lines[1].startswith("  abc     English"))


if __name__ == "__main__":
    unittest.main()
