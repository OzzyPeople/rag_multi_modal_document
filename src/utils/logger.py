# logger.py
"""
Centralized logging configuration for the RAG Multi-Doc project.
Provides console and file logging with automatic log rotation.
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
LOG_FILE = LOGS_DIR / f"rag_{datetime.now().strftime('%Y%m%d')}.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

# Default logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DETAILED_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"


def setup_logger(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_to_console: bool = True,
    detailed: bool = False
) -> logging.Logger:
    """
    Create and configure a logger instance.

    Args:
        name: Logger name (usually __name__ of the module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to write logs to file
        log_to_console: Whether to print logs to console
        detailed: Use detailed format with function names and line numbers

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Processing started")
        >>> logger.error("An error occurred", exc_info=True)
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)
    log_format = DETAILED_FORMAT if detailed else DEFAULT_FORMAT
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Console Handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File Handler (with rotation)
    if log_to_file:
        # Main log file (rotates at 10MB, keeps 5 backup files)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Error log file (only errors and critical)
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def set_log_level(logger: logging.Logger, level: int):
    """Set log level for logger and all its handlers."""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return setup_logger(name)


# Configure third-party library logging to reduce noise
def configure_external_loggers():
    """Reduce verbosity of third-party libraries."""
    # Set external libraries to WARNING level to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)


# Auto-configure external loggers on import
configure_external_loggers()
