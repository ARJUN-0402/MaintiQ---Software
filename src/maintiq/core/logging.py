"""Application logging configuration.

Uses a rotating file handler so logs do not grow without bound. Log files live in
the writable user-data logs directory. Raw input records and sensitive information
are intentionally not logged.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
import sys

from maintiq.config import get_config
from maintiq.core.exceptions import PathError

LOGGER_NAME = "maintiq"
LOG_FILENAME = "maintiq.log"
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB per log file
LOG_BACKUP_COUNT = 5

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _resolve_log_file() -> Path:
    """Return the path to the rotating log file."""
    config = get_config()
    log_dir = config.paths.logs_dir
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - environment dependent
        raise PathError(f"Unable to create log directory {log_dir}: {exc}") from exc
    return log_dir / LOG_FILENAME


def setup_logging(level: int = logging.INFO, log_to_console: bool = True) -> logging.Logger:
    """Initialise rotating file logging and return the application logger.

    Safe to call multiple times; repeated calls do not duplicate handlers.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called more than once.
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers):
        return logger

    try:
        log_file = _resolve_log_file()
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(_FORMATTER)
        logger.addHandler(file_handler)
    except PathError:
        # If logging to disk is impossible, continue with console-only logging.
        pass

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(_FORMATTER)
        logger.addHandler(console_handler)

    logger.info("MaintiQ logging initialised (level=%s)", logging.getLevelName(level))
    return logger
