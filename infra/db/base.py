# infra/db/base.py
from __future__ import annotations
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from pathlib import Path
import logging

from infra.path import default_db_path

logger = logging.getLogger(__name__)

Base = declarative_base()

# Build DB URL using the absolute path in AppData
db_path: Path = default_db_path()
# Make sure parent directory exists (should already be created in default_db_path)
db_path.parent.mkdir(parents=True, exist_ok=True)

db_url = f"sqlite:///{db_path.as_posix()}"
logger.info("Using SQLite database at: %s", db_url)

engine = create_engine(
    db_url,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)