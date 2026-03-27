import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from infra.platform.db.base import Base
from infra.platform.services import build_service_dict
from core.platform.notifications.domain_events import domain_events
from tests.path_rewrites import REPO_ROOT, resolve_repo_path
from tests.temp_dirs import cleanup_test_workspace, create_test_workspace

_ORIGINAL_PATH_READ_TEXT = Path.read_text
_ORIGINAL_PATH_EXISTS = Path.exists
_ORIGINAL_PATH_IS_DIR = Path.is_dir


def _patched_read_text(self: Path, *args, **kwargs):
    return _ORIGINAL_PATH_READ_TEXT(resolve_repo_path(self), *args, **kwargs)


def _patched_exists(self: Path):
    return _ORIGINAL_PATH_EXISTS(resolve_repo_path(self))


def _patched_is_dir(self: Path):
    return _ORIGINAL_PATH_IS_DIR(resolve_repo_path(self))


Path.read_text = _patched_read_text
Path.exists = _patched_exists
Path.is_dir = _patched_is_dir


@pytest.fixture(autouse=True)
def reset_test_domain_events():
    domain_events.reset()
    try:
        yield
    finally:
        domain_events.reset()


@pytest.fixture(autouse=True)
def bootstrap_admin_env(monkeypatch):
    monkeypatch.setenv("PM_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("PM_ADMIN_PASSWORD", "ChangeMe123!")
    monkeypatch.delenv("PM_ALLOW_DEFAULT_ADMIN_PASSWORD", raising=False)


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
    root = create_test_workspace("runtime")
    try:
        yield root
    finally:
        cleanup_test_workspace(root)


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

