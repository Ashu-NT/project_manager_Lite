from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.infra.persistence.db.engine import create_database_engine


def test_file_sqlite_uses_wal_and_bounded_busy_timeout(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'desktop.db').as_posix()}")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 15000
    finally:
        engine.dispose()


def test_file_sqlite_writer_commits_while_an_explicit_reader_is_open(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'concurrent.db').as_posix()}")
    sessions = sessionmaker(bind=engine, future=True)
    reader = sessions()
    writer = sessions()
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)"))
            connection.execute(text("INSERT INTO records (id, value) VALUES (1, 'before')"))

        # Force a real SQLite read transaction. This models a long-lived desktop
        # read session more strictly than Python sqlite's legacy SELECT behavior.
        reader.connection().exec_driver_sql("BEGIN")
        assert reader.execute(text("SELECT value FROM records WHERE id = 1")).scalar_one() == "before"

        writer.execute(text("UPDATE records SET value = 'after' WHERE id = 1"))
        writer.commit()
    finally:
        reader.rollback()
        reader.close()
        writer.close()
        engine.dispose()
