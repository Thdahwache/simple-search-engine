import json
import logging
import traceback
from datetime import datetime
from enum import Enum


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for log messages."""

    def format(self, record):
        """Format log record as JSON with standardized fields."""
        log_record = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "level": record.levelname,
            "context": record.__dict__.get("context", {}),
            "message": record.getMessage(),
            "service": "search-engine",  # Changed to reflect our service
        }

        # Add error details if present
        if hasattr(record, "exc_info") and record.exc_info:
            log_record["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)[-1].strip(),
            }

        return json.dumps(log_record)


class LogLevel(Enum):
    """Enumeration of available log levels."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Logger:
    """Standardized logger implementation with JSON formatting."""

    def __init__(self, log_level: LogLevel, name: str = "search-engine"):
        """Initialize logger with specified log level.

        Args:
            log_level (LogLevel): The minimum log level to record
            name (str): Service name for logging

        """
        handler = logging.StreamHandler()
        self._logger = logging.getLogger(name)
        self._logger.addHandler(handler)
        self._name = name
        self.__configure(log_level.value)

    def __configure(self, log_level: int):
        """Configure logger with JSON formatter and set log level."""
        formatter = JSONFormatter()
        loggers = [self._name, "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]

        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setFormatter(formatter)

    def __get_context(self, **kwargs):
        """Create context dictionary from keyword arguments."""
        return kwargs

    # Simplified logging methods with better context handling
    def log_search(self, query: str, results_count: int, time_ms: float, **kwargs):
        """Log search operation with performance metrics.

        Args:
            query (str): Search query
            results_count (int): Number of results found
            time_ms (float): Query execution time in milliseconds

        """
        context = {"query": query, "results": results_count, "execution_time_ms": time_ms, **kwargs}
        self._logger.info("Search executed", extra={"context": context})

    def log_debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._logger.debug(message, extra={"context": self.__get_context(**kwargs)})

    def log_info(self, message: str, **kwargs):
        """Log info message with context."""
        self._logger.info(message, extra={"context": self.__get_context(**kwargs)})

    def log_warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._logger.warning(message, extra={"context": self.__get_context(**kwargs)})

    def log_error(self, message: str, ex: Exception = None, **kwargs):
        """Log error message with exception details."""
        self._logger.error(
            message, exc_info=bool(ex), extra={"context": self.__get_context(**kwargs)}
        )

    def log_critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._logger.critical(message, extra={"context": self.__get_context(**kwargs)})
