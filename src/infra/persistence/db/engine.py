from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine

from infra.platform.path import default_db_path

logger = logging.getLogger(__name__)


def get_db_url() -> str:
    env_url = (os.getenv("PM_DB_URL") or "").strip()
    if env_url:
        parsed = urlparse(env_url)
        if parsed.scheme not in ("sqlite", "postgresql", "mysql", "oracle", "mssql"):
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
        logger.info("Using database URL from PM_DB_URL.")
        return env_url

    db_path: Path = default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.as_posix()}"
    logger.info("Using SQLite database at: %s", url)
    return url


db_url = get_db_url()
engine = create_engine(
    db_url,
    echo=False,
    future=True,
)

__all__ = ["db_url", "engine", "get_db_url"]
