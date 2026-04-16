from __future__ import annotations

import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from infra.platform.logging_config import setup_logging
from infra.platform.resource import resource_path
from src.infra.composition.app_container import build_service_dict
from src.infra.persistence.db.engine import get_db_url
from src.infra.persistence.db.session_factory import SessionLocal
from src.infra.persistence.migrations.runner import run_migrations
from src.ui.shell.login import prompt_for_login
from src.ui.shell.main_window import MainWindow
from ui.platform.settings import MainWindowSettingsStore
from ui.platform.shared.styles.theme import apply_app_style


def build_services() -> dict[str, object]:
    run_migrations(db_url=get_db_url())
    session = SessionLocal()
    return build_service_dict(session)


def main(argv: list[str] | None = None) -> int:
    setup_logging()

    app = QApplication(argv or sys.argv)
    settings_store = MainWindowSettingsStore()
    startup_theme = settings_store.load_theme_mode(default_mode=os.getenv("PM_THEME", "light"))
    startup_governance = settings_store.load_governance_mode(
        default_mode=os.getenv("PM_GOVERNANCE_MODE", "off")
    )
    os.environ["PM_THEME"] = startup_theme
    os.environ["PM_GOVERNANCE_MODE"] = startup_governance
    app.setWindowIcon(QIcon(resource_path("assets/icons/app.ico")))
    app.setFont(QFont("Segoe UI", 9))
    apply_app_style(app, mode=startup_theme)

    services = build_services()
    skip_login = os.getenv("PM_SKIP_LOGIN", "0").strip() in {"1", "true", "TRUE"}
    preauthenticated = bool(services["user_session"].is_authenticated())
    if (not skip_login or not preauthenticated) and not prompt_for_login(
        auth_service=services["auth_service"],
        user_session=services["user_session"],
    ):
        return 0

    window = MainWindow(services)
    window.show()
    return app.exec()


__all__ = ["build_services", "main"]
