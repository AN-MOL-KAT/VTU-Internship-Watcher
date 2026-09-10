import logging
import sys
from pathlib import Path
from typing import Optional

_LOGGER: Optional[logging.Logger] = None


def setup_logger(
    name: str = "vtu_watcher",
    log_file: Optional[str] = "logs/watcher.log",
    level: int = logging.INFO,
) -> logging.Logger:
    """Configures and returns the application logger."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    # Formatter for log output
    detailed_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    _LOGGER = logger
    return logger


def get_logger(name: str = "vtu_watcher") -> logging.Logger:
    """Returns an existing logger or sets up a new default logger."""
    global _LOGGER
    if _LOGGER is None:
        return setup_logger(name=name)
    return logging.getLogger(name)
