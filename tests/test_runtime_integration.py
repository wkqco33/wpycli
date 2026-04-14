from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wpycli import Command, ConfigSettings, LoggingSettings


RUNTIME_DEPS_AVAILABLE = (
    importlib.util.find_spec("wconfig") is not None and importlib.util.find_spec("wlogger") is not None
)


@unittest.skipUnless(RUNTIME_DEPS_AVAILABLE, "runtime dependencies are not installed")
class RuntimeIntegrationTests(unittest.TestCase):
    def test_runtime_bootstrap_uses_config_layers_and_flag_overrides(self) -> None:
        root = Command(use="app", version="1.0.0")
        root.add_persistent_string_flag("config", help="Path to config file")
        root.add_persistent_string_flag("log-level", help="Override log level")
        root.configure_runtime(
            config=ConfigSettings(
                defaults={
                    "server": {
                        "host": "127.0.0.1",
                    },
                    "logging": {
                        "level": "INFO",
                    },
                },
                env_prefix="APP",
                file_flag="config",
            ),
            logging=LoggingSettings(
                logger_name="testcli",
                level_flag="log-level",
            ),
        )

        captured: dict[str, object] = {}

        def run(ctx) -> int:
            captured["host"] = ctx.config.get("server.host")
            captured["logger_name"] = ctx.logger.name
            captured["level"] = ctx.logger.getEffectiveLevel()
            return 0

        root.add_command(Command(use="show", run=run))

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir, "config.yaml")
            config_path.write_text("server:\n  host: file-host\n", encoding="utf-8")
            with patch.dict(os.environ, {"APP_SERVER__HOST": "env-host"}, clear=False):
                exit_code = root.execute(["--config", str(config_path), "--log-level", "DEBUG", "show"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["host"], "env-host")
        self.assertEqual(captured["logger_name"], "testcli")
        self.assertEqual(captured["level"], logging.DEBUG)

    def test_version_flag_prints_root_version(self) -> None:
        root = Command(use="app", version="2.3.4")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = root.execute(["--version"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "2.3.4")


if __name__ == "__main__":
    unittest.main()
