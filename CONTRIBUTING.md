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

## Pull requests

- Keep changes focused and include tests for behavior changes.
- Update the README or changelog when user-facing behavior changes.
- Ensure the test suite passes before opening a pull request.
