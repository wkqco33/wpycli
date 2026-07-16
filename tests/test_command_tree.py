from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import unittest

from wpycli import Command


class CommandTreeTests(unittest.TestCase):
    def test_execution_flow_and_persistent_flags(self) -> None:
        events: list[tuple[object, ...]] = []

        root = Command(use="app")
        root.add_persistent_bool_flag("verbose", shorthand="v", help="Enable verbose output")
        root.persistent_pre_run = lambda ctx: events.append(("root-pre", ctx.flags["verbose"]))
        root.persistent_post_run = lambda ctx: events.append(("root-post", ctx.command.name))

        serve = Command(use="serve")
        serve.pre_run = lambda ctx: events.append(("serve-pre", tuple(ctx.args)))
        serve.run = lambda ctx: events.append(("run", ctx.command.full_path, ctx.flags["verbose"], tuple(ctx.args))) or 7
        serve.post_run = lambda ctx: events.append(("serve-post", ctx.command.name))
        root.add_command(serve)

        exit_code = root.execute(["serve", "--verbose", "alpha"])

        self.assertEqual(exit_code, 7)
        self.assertEqual(
            events,
            [
                ("root-pre", True),
                ("serve-pre", ("alpha",)),
                ("run", "app serve", True, ("alpha",)),
                ("serve-post", "serve"),
                ("root-post", "serve"),
            ],
        )

    def test_help_includes_local_and_inherited_flags(self) -> None:
        root = Command(use="app", short="Demo app")
        root.add_persistent_bool_flag("verbose", shorthand="v", help="Enable verbose output")
        serve = Command(use="serve", short="Serve traffic")
        serve.add_int_flag("port", help="Port to bind", default=8080, shorthand="p")
        root.add_command(serve)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = root.execute(["serve", "--help"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("+ app serve ", output)
        self.assertIn("Usage: app serve [flags] [args]", output)
        self.assertIn("FLAGS", output.upper())
        self.assertIn("--port INT", output)
        self.assertIn("--verbose", output)
        self.assertIn("Serve traffic", output)

    def test_unknown_flag_returns_usage_error(self) -> None:
        root = Command(use="app")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = root.execute(["--bogus"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("unknown flag '--bogus'", stderr.getvalue())
        self.assertIn("+ Error ", stderr.getvalue())

    def test_unexpected_exception_returns_exit_code_1(self) -> None:
        root = Command(use="app")
        def buggy_run(ctx):
            raise ZeroDivisionError("division by zero in handler")
        root.run = buggy_run
        
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = root.execute([])
            
        self.assertEqual(exit_code, 1)
        self.assertIn("System Error", stderr.getvalue())
        self.assertIn("division by zero", stderr.getvalue())

    def test_lineage_and_full_path_cache(self) -> None:
        root = Command(use="app")
        child = Command(use="child")
        
        self.assertEqual(child.full_path, "child")
        self.assertEqual(len(child.lineage()), 1)
        
        root.add_command(child)
        self.assertEqual(child.full_path, "app child")
        self.assertEqual(len(child.lineage()), 2)


if __name__ == "__main__":
    unittest.main()
