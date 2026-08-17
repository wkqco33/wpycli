# Contributing

## Development setup

This project requires Python 3.12 or newer. Install the development
environment with:

```bash
uv sync
```

Run the test suite with:

```bash
uv run python -m unittest discover -s tests
```

Check test coverage with:

```bash
uv run coverage run -m unittest discover -s tests
uv run coverage report
```

Check lint and formatting with:

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

## Pull requests

- Keep changes focused and include tests for behavior changes.
- Update the README or changelog when user-facing behavior changes.
- Use focused Conventional Commit-style messages, for example `fix(parser): reject missing flag values` or `feat(cli): add project command scaffolding`.
- Ensure the complete quality gate passes before opening a pull request.

## Release process

PyPI publishing is triggered by an annotated semantic-version tag such as `v0.2.0`.
Before creating the tag:

1. Update the version in `pyproject.toml` and the matching CLI version, if applicable.
2. Add a dated release entry to `CHANGELOG.md`.
3. Run the complete quality gate and build validation locally:

   ```bash
   uv sync --locked
   uv run python -m unittest discover -s tests
   uv run coverage run -m unittest discover -s tests
   uv run coverage report
   uv run ruff check .
   uv run ruff format --check .
   uv run basedpyright
   uv run python -m build
   uv run twine check dist/*
   ```

4. Create and push an annotated tag only after the release commit has been merged:

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

The publish workflow runs via GitHub Actions; no credentials or API tokens
should be committed to the repository.
