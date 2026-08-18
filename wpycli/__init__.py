from importlib.metadata import PackageNotFoundError, version

from .args import exact_args, max_args, min_args, range_args
from .command import Command
from .completion import (
    generate_bash_completion,
    generate_fish_completion,
    generate_zsh_completion,
)
from .context import CommandContext
from .docgen import generate_markdown_docs
from .errors import (
    BootstrapError,
    CLIError,
    UnknownCommandError,
    UnknownFlagError,
    UsageError,
)
from .output import Terminal
from .progress import ProgressBar, Spinner
from .runtime import ConfigSettings, LoggingSettings

try:
    __version__ = version("wpycli")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "BootstrapError",
    "CLIError",
    "Command",
    "CommandContext",
    "ConfigSettings",
    "LoggingSettings",
    "ProgressBar",
    "Spinner",
    "Terminal",
    "UnknownCommandError",
    "UnknownFlagError",
    "UsageError",
    "__version__",
    "exact_args",
    "generate_bash_completion",
    "generate_fish_completion",
    "generate_markdown_docs",
    "generate_zsh_completion",
    "max_args",
    "min_args",
    "range_args",
]
