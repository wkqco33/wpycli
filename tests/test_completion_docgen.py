from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from shutil import which

from wpycli import (
    Command,
    generate_bash_completion,
    generate_fish_completion,
    generate_markdown_docs,
    generate_zsh_completion,
)


def _build_tree() -> Command:
    root = Command(use="demo")
    root.add_persistent_bool_flag("verbose", shorthand="v")
    serve = Command(use="serve", short="serve traffic", run=lambda ctx: 0)
    serve.add_string_flag("host", default="127.0.0.1")
    config = Command(use="config", short="config commands")
    config.add_command(Command(use="show", short="show config", run=lambda ctx: 0))
    secret = Command(use="secret", short="internal", run=lambda ctx: 0, hidden=True)
    root.add_command(serve, config, secret)
    return root


class BashCompletionTests(unittest.TestCase):
    def test_includes_visible_commands_and_flags_not_hidden(self) -> None:
        script = generate_bash_completion(_build_tree())

        self.assertIn('_completions[""]="serve config --verbose -v"', script)
        self.assertIn('_completions["serve"]="--verbose -v --host"', script)
        self.assertIn('_completions["config"]="show --verbose -v"', script)
        self.assertNotIn("secret", script)

    @unittest.skipUnless(which("bash"), "bash not available")
    def test_generated_script_is_syntactically_valid(self) -> None:
        script = generate_bash_completion(_build_tree())
        result = subprocess.run(
            ["bash", "-n"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class ZshCompletionTests(unittest.TestCase):
    def test_wraps_bash_completion_with_bashcompinit(self) -> None:
        script = generate_zsh_completion(_build_tree())
        self.assertIn("#compdef demo", script)
        self.assertIn("bashcompinit", script)
        self.assertIn('_completions[""]="serve config --verbose -v"', script)


class FishCompletionTests(unittest.TestCase):
    def test_includes_visible_commands_and_flags_not_hidden(self) -> None:
        script = generate_fish_completion(_build_tree())

        self.assertIn(
            'complete -c demo -n "__fish_use_subcommand" -f -a "serve"', script
        )
        self.assertIn(
            'complete -c demo -n "__fish_seen_subcommand_from serve" -l host', script
        )
        self.assertNotIn("secret", script)


class CompletionCommandTests(unittest.TestCase):
    def test_completion_command_is_hidden_and_prints_script(self) -> None:
        root = _build_tree()
        root.add_command(Command(use="serve2", run=lambda ctx: 0))
        root.add_completion_command()

        self.assertNotIn("completion", root.help_text())

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = root.execute(["completion", "bash"])

        self.assertEqual(exit_code, 0)
        self.assertIn("_demo_complete", stdout.getvalue())

    def test_missing_shell_argument_is_usage_error(self) -> None:
        root = _build_tree()
        root.add_completion_command()
        with redirect_stdout(io.StringIO()):
            exit_code = root.execute(["completion"])
        self.assertEqual(exit_code, 2)

    def test_unsupported_shell_is_usage_error(self) -> None:
        root = _build_tree()
        root.add_completion_command()
        with redirect_stdout(io.StringIO()):
            exit_code = root.execute(["completion", "powershell"])
        self.assertEqual(exit_code, 2)


class MarkdownDocsTests(unittest.TestCase):
    def test_generates_one_file_per_visible_command(self) -> None:
        root = _build_tree()
        with tempfile.TemporaryDirectory() as tmp:
            written = generate_markdown_docs(root, tmp)
            names = {p.name for p in written}

        self.assertEqual(
            names, {"demo.md", "demo_serve.md", "demo_config.md", "demo_config_show.md"}
        )

    def test_inherited_flags_shown_on_child_not_root(self) -> None:
        root = _build_tree()
        with tempfile.TemporaryDirectory() as tmp:
            generate_markdown_docs(root, tmp)
            root_doc = Path(tmp, "demo.md").read_text()
            child_doc = Path(tmp, "demo_config.md").read_text()

        self.assertIn("## Flags", root_doc)
        self.assertNotIn("## Inherited Flags", root_doc)
        self.assertIn("## Inherited Flags", child_doc)
        self.assertIn("--verbose", child_doc)

    def test_subcommand_links_and_hidden_exclusion(self) -> None:
        root = _build_tree()
        with tempfile.TemporaryDirectory() as tmp:
            generate_markdown_docs(root, tmp)
            root_doc = Path(tmp, "demo.md").read_text()

        self.assertIn("[demo serve](demo_serve.md)", root_doc)
        self.assertNotIn("secret", root_doc)


if __name__ == "__main__":
    unittest.main()
