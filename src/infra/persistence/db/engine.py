from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url

from src.infra.platform.env_loader import load_env_file
from src.infra.platform.path import default_db_path

logger = logging.getLogger(__name__)
sql_logger = logging.getLogger("sqlalchemy.diagnostics")
_query_state = threading.local()

load_env_file()

_SLOW_QUERY_MS = float(os.getenv("PM_SLOW_QUERY_MS", "250") or 250)
_TRACE_SQL = (os.getenv("PM_SQL_TRACE", "0") or "").strip().lower() in {"1", "true", "yes"}
_SQLITE_BUSY_TIMEOUT_MS = max(
    0, int(os.getenv("PM_SQLITE_BUSY_TIMEOUT_MS", "15000") or 15000)
)
_LOGGED_DB_URLS: set[str] = set()


def _log_db_url_once(url: str, message: str) -> None:
    if not logging.getLogger().handlers or url in _LOGGED_DB_URLS:
        return
    logger.info(message, url)
    _LOGGED_DB_URLS.add(url)


def get_db_url() -> str:
    env_url = (os.getenv("PM_DB_URL") or "").strip()
    if env_url:
        parsed = urlparse(env_url)
        base_scheme = parsed.scheme.split("+", 1)[0]
        if base_scheme not in ("sqlite", "postgresql", "mysql", "oracle", "mssql"):
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
        _log_db_url_once(env_url, "Using database URL from PM_DB_URL: %s")
        return env_url

    db_path: Path = default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.as_posix()}"
    _log_db_url_once(url, "Using SQLite database at: %s")
    return url


def create_database_engine(url: str) -> Engine:
    """Build the process engine with the supported desktop database policy."""
    parsed = make_url(url)
    connect_args: dict[str, object] = {}
    if parsed.get_backend_name() == "sqlite":
        connect_args["timeout"] = _SQLITE_BUSY_TIMEOUT_MS / 1000

    database_engine = create_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )
    if parsed.get_backend_name() == "sqlite":
        event.listen(database_engine, "connect", _configure_sqlite_connection)
    return database_engine


def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    # WAL permits the operation-scoped command UoWs to commit while the desktop
    # read session is active. The timeout remains a bounded fallback for brief
    # writer contention; it is not an application-level retry policy.
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


db_url = get_db_url()
engine = create_database_engine(db_url)


@event.listens_for(engine, "before_cursor_execute")
def _log_before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    _query_state.started_at = perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _log_after_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    started = getattr(_query_state, "started_at", None)
    if started is None:
        return
    duration_ms = (perf_counter() - started) * 1000
    statement_summary = " ".join(str(statement or "").split())[:240]
    row_count = getattr(cursor, "rowcount", -1)
    if duration_ms >= _SLOW_QUERY_MS:
        sql_logger.warning(
            "Slow SQL query duration_ms=%.1f row_count=%s executemany=%s statement=%s",
            duration_ms,
            row_count,
            executemany,
            statement_summary,
        )
    elif _TRACE_SQL:
        sql_logger.debug(
            "SQL query duration_ms=%.1f row_count=%s executemany=%s statement=%s",
            duration_ms,
            row_count,
            executemany,
            statement_summary,
        )

__all__ = ["create_database_engine", "db_url", "engine", "get_db_url"]
