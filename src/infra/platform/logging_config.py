# src/infra/platform/logging_config.py
from __future__ import annotations
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from src.infra.platform.path import user_data_dir
from src.infra.platform.operational_support import (
    TraceIdLogFilter,
    get_operational_support,
    install_global_exception_hooks,
)

_LOGGING_CONFIGURED = False
_QT_MESSAGE_HANDLER_INSTALLED = False


def _resolve_log_level() -> int:
    raw_level = (os.getenv("PM_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "DEBUG").strip().upper()
    return getattr(logging, raw_level, logging.DEBUG)


def _install_qt_message_handler() -> None:
    global _QT_MESSAGE_HANDLER_INSTALLED
    if _QT_MESSAGE_HANDLER_INSTALLED:
        return

    qt_logger = logging.getLogger("qt.qml")

    def _handler(message_type, context, message: str) -> None:
        if message_type == QtMsgType.QtDebugMsg:
            level = logging.DEBUG
        elif message_type == QtMsgType.QtInfoMsg:
            level = logging.INFO
        elif message_type == QtMsgType.QtWarningMsg:
            level = logging.WARNING
        elif message_type == QtMsgType.QtCriticalMsg:
            level = logging.ERROR
        else:
            level = logging.CRITICAL
        file_name = getattr(context, "file", "") or ""
        function = getattr(context, "function", "") or ""
        category = getattr(context, "category", "") or ""
        line = int(getattr(context, "line", 0) or 0)
        qt_logger.log(
            level,
            "Qt/QML message type=%s category=%s file=%s line=%s function=%s message=%s",
            getattr(message_type, "name", str(message_type)),
            category or "-",
            file_name or "-",
            line,
            function or "-",
            message,
        )

    qInstallMessageHandler(_handler)
    _QT_MESSAGE_HANDLER_INSTALLED = True
    logging.getLogger(__name__).info("Qt/QML message handler installed.")


def setup_logging() -> Path:
    """
    Configure application logging.
    Logs go to the per-user AppData directory, not Program Files.
    """
    global _LOGGING_CONFIGURED
    log_dir: Path = user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"
    if _LOGGING_CONFIGURED:
        logging.getLogger(__name__).debug(
            "Logging setup skipped because it is already configured. path=%s",
            log_file,
        )
        return log_file

    logger = logging.getLogger()
    log_level = _resolve_log_level()
    logger.setLevel(log_level)

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
        "%(asctime)s [%(levelname)s] trace=%(trace_id)s "
        "thread=%(threadName)s:%(thread)d %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Optional: console handler (useful in dev, harmless in frozen app)
    console = logging.StreamHandler()
    console.addFilter(trace_filter)
    console.setFormatter(
        logging.Formatter(
            "%(levelname)s [trace=%(trace_id)s] [%(threadName)s]: %(message)s"
        )
    )
    logger.addHandler(console)

    _LOGGING_CONFIGURED = True
    install_global_exception_hooks()
    _install_qt_message_handler()
    logger.info(
        "Logging initialized. path=%s level=%s rotating_max_bytes=%s backups=%s",
        log_file,
        logging.getLevelName(log_level),
        1_000_000,
        5,
    )
    get_operational_support().emit_event(
        event_type="app.logging.initialized",
        message=f"Logging initialized at {log_file}",
        data={"log_file": str(log_file), "level": logging.getLevelName(log_level)},
    )
    return log_file
