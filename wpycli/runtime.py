from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from .flags import FlagValue

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class RuntimeSetupError(RuntimeError):
    """Raised for expected configuration or logging bootstrap failures."""


def _flag_override(
    flag_values: Mapping[str, FlagValue], flag_name: str | None
) -> FlagValue:
    if not flag_name:
        return None
    value = flag_values.get(flag_name)
    if value in {None, ""}:
        return None
    return value


@dataclass(slots=True)
class ConfigSettings:
    defaults: Mapping[str, Any] | None = None
    files: tuple[str, ...] = ()
    dotenv: str | None = None
    env: bool = True
    env_prefix: str | None = None
    env_prefix_separator: str = "_"
    env_nested_delimiter: str = "__"
    file_flag: str | None = None
    dotenv_flag: str | None = None

    def build(self, flag_values: Mapping[str, FlagValue]) -> Any:
        try:
            from wconfig import load_config
        except ImportError as exc:
            raise RuntimeSetupError(
                "wpyconf must be installed to use configuration bootstrap"
            ) from exc

        files = list(self.files)
        file_override = _flag_override(flag_values, self.file_flag)
        if file_override is not None:
            files.append(str(file_override))

        dotenv = self.dotenv
        dotenv_override = _flag_override(flag_values, self.dotenv_flag)
        if dotenv_override is not None:
            dotenv = str(dotenv_override)

        return load_config(
            defaults=self.defaults,
            files=tuple(files),
            dotenv=dotenv,
            env=self.env,
            env_prefix=self.env_prefix,
            env_prefix_separator=self.env_prefix_separator,
            env_nested_delimiter=self.env_nested_delimiter,
        )


@dataclass(slots=True)
class LoggingSettings:
    logger_name: str | None = None
    default_level: LogLevel = "INFO"
    level_key: str = "logging.level"
    log_file_key: str = "logging.file"
    max_bytes_key: str = "logging.max_bytes"
    backup_count_key: str = "logging.backup_count"
    level_flag: str | None = None
    log_file_flag: str | None = None

    def build(
        self,
        *,
        command_name: str,
        config: Any,
        flag_values: Mapping[str, FlagValue],
    ) -> logging.Logger:
        try:
            import wlogger
        except ImportError as exc:
            raise RuntimeSetupError(
                "wpylog must be installed to use logging bootstrap"
            ) from exc

        def from_config(key: str, default: Any = None) -> Any:
            if config is None:
                return default
            return config.get(key, default)

        level = _flag_override(flag_values, self.level_flag) or from_config(
            self.level_key, self.default_level
        )
        log_file_value = _flag_override(flag_values, self.log_file_flag) or from_config(
            self.log_file_key
        )
        log_file = None if log_file_value is None else str(log_file_value)
        max_bytes = from_config(self.max_bytes_key, 10 * 1024 * 1024)
        backup_count = from_config(self.backup_count_key, 5)

        wlogger.setup(
            level=cast(LogLevel, str(level).upper()),
            log_file=log_file,
            max_bytes=int(max_bytes),
            backup_count=int(backup_count),
        )
        logger_name = self.logger_name or command_name.replace(" ", ".")
        return wlogger.get_logger(logger_name)


@dataclass(slots=True)
class RuntimeBundle:
    config: Any = None
    logger: logging.Logger | None = None


def bootstrap_runtime(
    *,
    command_name: str,
    flag_values: Mapping[str, FlagValue],
    config_settings: ConfigSettings | None,
    logging_settings: LoggingSettings | None,
) -> RuntimeBundle:
    try:
        config = config_settings.build(flag_values) if config_settings else None
        logger = (
            logging_settings.build(
                command_name=command_name, config=config, flag_values=flag_values
            )
            if logging_settings
            else None
        )
    except RuntimeSetupError:
        raise
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise RuntimeSetupError(str(exc)) from exc
    return RuntimeBundle(config=config, logger=logger)
