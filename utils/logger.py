"""
utils/logger.py
---------------
Application-wide logging setup.

Provides a rotating file logger that writes to:
  ~/.Neuro-Gaze/app.log

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Something happened")
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Directory for log files
_LOG_DIR = os.path.join(os.path.expanduser("~"), ".Neuro-Gaze")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")

# Ensure log directory exists
os.makedirs(_LOG_DIR, exist_ok=True)

# Root logger configuration (set once)
_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger("Neuro-Gaze")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler — max 5 MB, keep 3 backups
    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'Neuro-Gaze' namespace."""
    _configure_root_logger()
    return logging.getLogger(f"Neuro-Gaze.{name}")
