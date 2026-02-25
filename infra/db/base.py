# infra/db/base.py
from __future__ import annotations
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from pathlib import Path
import logging
import os

from infra.path import default_db_path

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_db_url() -> str:
    env_url = (os.getenv("PM_DB_URL") or "").strip()
    if env_url:
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

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
