# logger.py — Centralised Logger Factory for FL-CL
#
# Provides a single get_logger(name) call that returns a pre-configured
# logging.Logger instance for any src/ module.
#
# Configuration:
# - Log level: controlled by FL_LOG_LEVEL environment variable (default: INFO).
# - Format:    [%(name)s] %(levelname)s: %(message)s
# - Handler:   StreamHandler to stderr (no file sink — RAMDisk mandate).
#
# Usage:
# from logger import get_logger
# logger = get_logger(__name__)
# logger.info("Training complete")
# logger.warning("JSD gate failed: %.4f", jsd)

import logging
import os

_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_FORMAT = "[%(name)s] %(levelname)s: %(message)s"
_initialized: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """
    Return a Logger for *name*, initialising it exactly once.

    The effective level is read from the FL_LOG_LEVEL environment variable
    (case-insensitive). Falls back to INFO if the variable is absent or
    contains an unrecognised value.

    Args:
        name: Logger name — typically __name__ of the calling module.

    Returns:
        logging.Logger: Configured logger ready for use.
    """
    logger = logging.getLogger(name)

    if name not in _initialized:
        level_str = os.environ.get("FL_LOG_LEVEL", "INFO").upper()
        level = _LEVEL_MAP.get(level_str, logging.INFO)

        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            formatter = logging.Formatter(_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Prevent log records from propagating to the root logger and
        # appearing twice when the calling process has a root handler set.
        logger.propagate = False
        _initialized.add(name)

    return logger
