from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

from sqlalchemy import create_engine, event

from src.infra.platform.path import default_db_path

logger = logging.getLogger(__name__)
sql_logger = logging.getLogger("sqlalchemy.diagnostics")
_query_state = threading.local()
_SLOW_QUERY_MS = float(os.getenv("PM_SLOW_QUERY_MS", "250") or 250)
_TRACE_SQL = (os.getenv("PM_SQL_TRACE", "0") or "").strip().lower() in {"1", "true", "yes"}
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
        if parsed.scheme not in ("sqlite", "postgresql", "mysql", "oracle", "mssql"):
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
        _log_db_url_once(env_url, "Using database URL from PM_DB_URL: %s")
        return env_url

    db_path: Path = default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.as_posix()}"
    _log_db_url_once(url, "Using SQLite database at: %s")
    return url


db_url = get_db_url()
engine = create_engine(
    db_url,
    echo=False,
    future=True,
)


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

__all__ = ["db_url", "engine", "get_db_url"]
