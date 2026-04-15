from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from src.infra.persistence.db.engine import engine


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

__all__ = ["SessionLocal"]
