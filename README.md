# wpycli

`wpycli` is a Cobra-inspired CLI toolkit for Python 3.12+.

It provides:

- hierarchical commands and aliases
- local and persistent flags
- automatic `--help`, `help`, and `--version`
- hook-based execution flow
- layered configuration bootstrap via `wconfig`
- logging bootstrap via `wlogger`
- polished terminal output with colors, panels, and structured help without `rich`

The project consumes `wlogger` and `wconfig` directly from `https://pypi.wkqcosoft.cloud`.

## Install

```bash
pip install .
```

Because `pyproject.toml` uses direct wheel URLs, installation pulls `wlogger` and `wconfig` from the hosted PyPI server automatically.

## Example

```bash
python main.py --help
python main.py serve --config ./config.yaml
python main.py --log-level DEBUG config
python main.py echo hello world
```

## Programming model

```python
from wpycli import Command, ConfigSettings, LoggingSettings

root = Command(
    use="demo",
    short="Demo CLI",
    version="0.1.0",
)

root.add_persistent_string_flag("config", help="Path to config file")
root.add_persistent_string_flag("log-level", help="Override log level")

root.configure_runtime(
    config=ConfigSettings(
        defaults={"logging": {"level": "INFO"}},
        env_prefix="DEMO",
        file_flag="config",
    ),
    logging=LoggingSettings(
        logger_name="demo",
        level_flag="log-level",
    ),
)

def run(ctx):
    ctx.logger.info("running %s", ctx.command.full_path)
    print(ctx.config.as_dict())

show = Command(use="show", short="Print configuration", run=run)
root.add_command(show)

raise SystemExit(root.execute())
```

## Cobra-inspired behavior

- root command owns the command tree
- child commands are registered explicitly with `add_command()`
- persistent flags flow from parent to child
- execution order is `persistent_pre_run* -> pre_run -> run -> post_run -> persistent_post_run*`
- help text is generated from command metadata and registered flags
- terminal rendering uses an internal lightweight formatter instead of the `rich` dependency

## Development

```bash
python -m unittest discover -s tests
```
