# Project Guide for Coding Agents

## Scope

This file applies to the entire `wpycli` repository. Keep changes focused on the requested task and do not commit or create branches unless explicitly asked.

## Project

- Python package targeting Python 3.12+.
- Package source: `wpycli/`
- Tests: `tests/`
- CLI entry points:
  - `wpycli = wpycli.cli.main:main`
  - development example: `main.py`
- Package dependencies include `wpyconf` and `wpylog`.

## Development commands

Synchronize the locked environment before working:

```bash
uv sync --locked
```

Run the complete quality gate locally:

```bash
uv run python -m unittest discover -s tests
uv run coverage run -m unittest discover -s tests
uv run coverage report
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

The coverage threshold is configured in `pyproject.toml`; do not lower it to make a change pass. Add or improve tests instead.

## TDD workflow

1. Reproduce the requested behavior or bug with a focused failing test.
2. Make the smallest production change that makes the test pass.
3. Refactor only after the focused test and the full suite pass.
4. Preserve tests for public CLI behavior, exit codes, output, errors, and edge cases.
5. Run the complete quality gate before reporting completion.

Use `unittest` style consistent with the existing suite. Prefer public APIs and observable behavior over testing private implementation details.

## Test design

- Keep tests deterministic and independent.
- Redirect or inject terminal streams instead of depending on a real TTY.
- Use temporary directories for filesystem behavior and always clean them up.
- Runtime integration tests may require the installed `wpyconf`/`wpylog` packages; do not silently weaken assertions when those dependencies are available.
- When adding a regression test, put it near the relevant feature or in a focused `tests/test_quality_edges.py` file if it spans multiple low-level modules.

## Code conventions

- Keep type annotations compatible with Python 3.12.
- Use `collections.abc` for collection protocols and `typing.Self` where appropriate.
- Keep imports Ruff-sorted and format with Ruff.
- Avoid introducing new `Any`; prefer concrete types, protocols, or narrow unions. Existing dynamic configuration boundaries should be isolated and documented by types.
- Preserve the CLI's existing exit-code and error-rendering behavior.
- Do not add dependencies unless they are needed for the requested behavior and are recorded in `pyproject.toml` and `uv.lock`.

## Architecture notes

- `command.py` owns command-tree construction and execution.
- `parser.py` resolves argv into an invocation.
- `flags.py` owns flag definitions and conversion.
- `context.py` defines handler context and callback types.
- `output.py`, `help.py`, and `progress.py` handle terminal presentation.
- `runtime.py` integrates optional configuration and logging services.
- `cli/` contains the built-in project-management commands and templates.

`TYPE_CHECKING` imports are used to avoid runtime dependency cycles. Be careful when changing type-only imports; `reportImportCycles` is disabled because these annotations are intentionally non-runtime imports, not because new runtime cycles are acceptable.

## CI expectations

GitHub Actions runs tests, coverage, Ruff lint/format checks, and BasedPyright on Python 3.12 and 3.13. A change is not complete if any of these checks fail.

When a diagnostic comes from a third-party package's incomplete type information, isolate the boundary with a narrow annotation or cast and explain the reason in the code or final report. Do not broadly disable type checking to hide application errors.
