"""Tests for logging initialization."""

import dataclasses
import logging
import logging.handlers

import maintiq.config as config_module
import maintiq.core.logging as logging_module
from maintiq.core.logging import LOGGER_NAME, setup_logging


def test_logging_initializes_and_writes_test_message(tmp_path, monkeypatch):
    """Logging can initialize and write a test message to a temp logs directory."""
    fake_logs = tmp_path / "logs"
    fake_config = config_module.get_config()

    new_paths = dataclasses.replace(fake_config.paths, logs_dir=fake_logs)
    new_config = dataclasses.replace(fake_config, paths=new_paths)

    # setup_logging resolves get_config through this module's namespace.
    monkeypatch.setattr(logging_module, "get_config", lambda: new_config)

    # Avoid duplicate-handler short-circuit from a prior call.
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers = [
        h for h in logger.handlers if not isinstance(h, logging.handlers.RotatingFileHandler)
    ]

    setup_logging(level=logging.DEBUG, log_to_console=False)
    assert logger.name == LOGGER_NAME
    assert logger.level == logging.DEBUG

    test_message = "maintiq phase 0 logging test message"
    logger.debug(test_message)

    log_files = list(fake_logs.glob("*.log*"))
    assert log_files, f"No log files created in {fake_logs}"
    contents = "".join(f.read_text(encoding="utf-8") for f in log_files)
    assert test_message in contents
