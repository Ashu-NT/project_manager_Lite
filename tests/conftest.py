import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from infra.db.base import Base
from infra.services import build_service_dict


@pytest.fixture
def session():
    # separate in-memory DB for tests
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def repo_workspace():
    root = Path(__file__).resolve().parents[1] / "pytest_runtime_workspace" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def tmp_path(repo_workspace):
    path = repo_workspace / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def services(session):
    graph = build_service_dict(session)
    auth = graph["auth_service"]
    user_session = graph["user_session"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(admin))
    return graph


@pytest.fixture
def anonymous_services(session):
    return build_service_dict(session)

