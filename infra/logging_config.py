# infra/logging_config.py
from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from infra.path import user_data_dir  # or infra.paths if that's your filename
from infra.operational_support import (
    TraceIdLogFilter,
    get_operational_support,
    install_global_exception_hooks,
)

def setup_logging():
    """
    Configure application logging.
    Logs go to the per-user AppData directory, not Program Files.
    """
    log_dir: Path = user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear any existing handlers (important in PyInstaller single-process)
    logger.handlers.clear()

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,  # 1 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    trace_filter = TraceIdLogFilter()
    file_handler.addFilter(trace_filter)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] trace=%(trace_id)s %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Optional: console handler (useful in dev, harmless in frozen app)
    console = logging.StreamHandler()
    console.addFilter(trace_filter)
    console.setFormatter(logging.Formatter("%(levelname)s [trace=%(trace_id)s]: %(message)s"))
    logger.addHandler(console)

    logger.info("Logging initialized. Log file at %s", log_file)
    install_global_exception_hooks()
    get_operational_support().emit_event(
        event_type="app.logging.initialized",
        message=f"Logging initialized at {log_file}",
        data={"log_file": str(log_file)},
    )
