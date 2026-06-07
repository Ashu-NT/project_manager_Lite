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


def _debug_logging_enabled() -> bool:
    return (os.getenv("PM_DEBUG_LOGGING") or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_log_level() -> int:
    default_level = "DEBUG" if _debug_logging_enabled() else "INFO"
    raw_level = (os.getenv("PM_LOG_LEVEL") or os.getenv("LOG_LEVEL") or default_level).strip().upper()
    return getattr(logging, raw_level, logging.INFO)


def _apply_logger_overrides(root_level: int) -> None:
    debug_enabled = root_level <= logging.DEBUG
    debug_or_info = logging.DEBUG if debug_enabled else logging.INFO
    overrides = {
        "src.ui_qml.shared.models.data_table_model": debug_or_info,
        "src.ui_qml.modules.project_management.controllers.common.workspace_controller_base": debug_or_info,
        "src.ui_qml.platform.controllers.common.workspace_controller_base": debug_or_info,
        "src.ui_qml.modules.inventory_procurement.controllers.common.workspace_controller_base": debug_or_info,
        "src.ui_qml.modules.maintenance.controllers.common.workspace_controller_base": debug_or_info,
        "src.core.platform.calendar.application.enterprise_calendar_resolver": debug_or_info,
        "qt.qml": logging.DEBUG if debug_enabled else logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "alembic": logging.INFO,
        "alembic.runtime.migration": logging.WARNING,
    }
    for logger_name, level in overrides.items():
        logging.getLogger(logger_name).setLevel(level)


def _should_log_qt_message(level: int) -> bool:
    return level >= logging.WARNING or logging.getLogger("qt.qml").isEnabledFor(level)


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
        if not _should_log_qt_message(level):
            return
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
    logging.getLogger(__name__).debug("Qt/QML message handler installed.")


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
    _apply_logger_overrides(log_level)
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
