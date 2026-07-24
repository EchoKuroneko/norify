import logging
import sys
import os
from pathlib import Path
from typing import Any, Dict

app_name = "Norify"
app_data_dir = Path(os.environ.get("APPDATA", Path.home())) / app_name
app_data_dir.mkdir(parents=True, exist_ok=True)
LOG_FILE = app_data_dir / f"{app_name.lower()}.log"

# Standard attributes defined on standard LogRecord instances
STANDARD_LOG_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class ExtraContextFormatter(logging.Formatter):
    """Custom formatter that automatically appends any `extra={...}` payload key-values to the log line."""

    def format(self, record: logging.LogRecord) -> str:
        # Standard formatted log string
        log_line = super().format(record)

        # Extract extra context variables
        extra_ctx: Dict[str, Any] = {
            k: v
            for k, v in record.__dict__.items()
            if k not in STANDARD_LOG_RECORD_ATTRS
        }

        if extra_ctx:
            # Format extra context as ` key=value` or ` [key=value]`
            ctx_str = " ".join(f"{k}={v!r}" for k, v in extra_ctx.items())
            log_line = f"{log_line} | Context: {ctx_str}"

        return log_line


def setup_logger(name: str = "Norify") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    # Formatting template
    formatter = ExtraContextFormatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
