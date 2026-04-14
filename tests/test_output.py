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


if __name__ == "__main__":
    unittest.main()
