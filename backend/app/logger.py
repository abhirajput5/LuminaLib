from __future__ import annotations

import json
import logging
import os
from typing import Optional, Any, Dict


def flatten_dict(
    data: Dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> Dict[str, Any]:
    """
    Recursively flatten nested dictionaries.

    Example:
    {"a": {"b": 1}} → {"a.b": 1}
    """
    items: Dict[str, Any] = {}

    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, sep))
        else:
            items[new_key] = value

    return items


class JsonLogFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": getattr(record, "service", None) or self.service_name,
            "request_id": getattr(record, "request_id", None),
        }

        # Standard attributes to ignore
        standard_attrs = set(vars(logging.LogRecord("", 0, "", 0, "", (), None)))

        # Extract custom fields
        extra_data: Dict[str, Any] = {}

        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                extra_data[key] = value

        # 🔥 Flatten everything
        flattened_extra = flatten_dict(extra_data)

        # Merge into log
        log.update(flattened_extra)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for CLI logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        return (
            f"[{self.formatTime(record)}] "
            f"{record.levelname:<8} "
            f"{record.name}: "
            f"{record.getMessage()}"
        )


class LoggerFactory:
    """
    Central logging configuration for the application.

    Supports:
    - JSON structured logs (file, Loki-friendly)
    - Human-readable console logs
    - Per-service configuration
    """

    _configured: bool = False

    @classmethod
    def configure(
        cls,
        *,
        service_name: str,
        log_file: str,
        level: int = logging.INFO,
    ) -> None:
        """
        Configure root logger (only once per process).

        Args:
            service_name: logical name (backend, celery)
            log_file: absolute path inside container (/logs/backend.log)
            level: logging level
        """

        if cls._configured:
            return

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Remove default handlers (avoid duplication)
        root_logger.handlers.clear()

        # Create formatters
        json_formatter = JsonLogFormatter(service_name=service_name)
        console_formatter = ConsoleFormatter()

        # Console handler (human-readable)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)

        # File handler (structured JSON)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)

        # Attach handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        cls._configured = True

    @staticmethod
    def get_logger(name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance.
        """
        return logging.getLogger(name or "app")
