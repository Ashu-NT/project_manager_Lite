from __future__ import annotations

import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.infra.platform.logging_config import setup_logging
from src.infra.platform.resource import resource_path
from src.api.desktop.runtime import build_desktop_api_registry
from src.infra.composition.app_container import build_service_dict
from src.infra.persistence.db.engine import get_db_url
from src.infra.persistence.db.session_factory import SessionLocal
from src.infra.persistence.migrations.runner import run_migrations
from src.ui.shell.login import prompt_for_login
from src.ui.shell.main_window import MainWindow
from src.ui.platform.settings import MainWindowSettingsStore
from src.ui.shared.formatting.theme import apply_app_style


def build_services() -> dict[str, object]:
    run_migrations(db_url=get_db_url())
    session = SessionLocal()
    services = build_service_dict(session)
    desktop_api_registry = build_desktop_api_registry(services)
    services["desktop_api_registry"] = desktop_api_registry
    services["desktop_platform_runtime_api"] = desktop_api_registry.platform_runtime
    services["desktop_platform_site_api"] = desktop_api_registry.platform_site
    services["desktop_platform_department_api"] = desktop_api_registry.platform_department
    services["desktop_platform_employee_api"] = desktop_api_registry.platform_employee
    services["desktop_platform_access_api"] = desktop_api_registry.platform_access
    services["desktop_platform_approval_api"] = desktop_api_registry.platform_approval
    services["desktop_platform_audit_api"] = desktop_api_registry.platform_audit
    services["desktop_platform_document_api"] = desktop_api_registry.platform_document
    services["desktop_platform_party_api"] = desktop_api_registry.platform_party
    services["desktop_platform_support_api"] = desktop_api_registry.platform_support
    services["desktop_platform_user_api"] = desktop_api_registry.platform_user
    return services


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
