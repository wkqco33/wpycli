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
- Ensure the test suite passes before opening a pull request.
