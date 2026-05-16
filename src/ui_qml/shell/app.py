from __future__ import annotations

import os
import sys

from PySide6.QtCore import QEventLoop
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.api.desktop.runtime import build_desktop_api_registry
from src.infra.composition.app_container import build_service_dict
from src.infra.persistence.db.engine import get_db_url
from src.infra.persistence.db.session_factory import SessionLocal
from src.infra.persistence.migrations.runner import run_migrations
from src.infra.platform.app_settings import AppSettingsStore
from src.infra.platform.logging_config import setup_logging
from src.infra.platform.resource import resource_path

from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.ui_qml.modules.maintenance.context import MaintenanceWorkspaceCatalog
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context, update_shell_runtime_state
from src.ui_qml.shell.login import ShellLoginController
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import (
    create_qml_engine,
    load_qml,
)
from src.ui_qml.shell.qml_registry import build_qml_route_registry
from src.ui_qml.shell.routes import shell_qml_path


def build_services() -> dict[str, object]:
    run_migrations(db_url=get_db_url())
    session = SessionLocal()
    services = build_service_dict(session)
    desktop_api_registry = build_desktop_api_registry(services)
    services["desktop_api_registry"] = desktop_api_registry
    return services


def _configure_runtime_environment(app: QApplication, *, settings_store: AppSettingsStore) -> tuple[str, str]:
    startup_theme = settings_store.load_theme_mode(default_mode=os.getenv("PM_THEME", "light"))
    startup_governance = settings_store.load_governance_mode(
        default_mode=os.getenv("PM_GOVERNANCE_MODE", "off")
    )
    os.environ["PM_THEME"] = startup_theme
    os.environ["PM_GOVERNANCE_MODE"] = startup_governance
    app.setWindowIcon(QIcon(resource_path("assets/icons/app.ico")))
    app.setFont(QFont("Segoe UI", 9))
    return startup_theme, startup_governance


def _prompt_for_login_qml(*, auth_service, user_session) -> bool:
    controller = ShellLoginController(
        auth_service=auth_service,
        user_session=user_session,
    )
    engine = create_qml_engine()
    load_qml(
        engine,
        shell_qml_path("LoginWindow.qml"),
        initial_properties={"loginController": controller},
    )
    login_loop = QEventLoop()
    accepted = {"value": False}

    def _accept() -> None:
        accepted["value"] = True
        login_loop.quit()

    def _reject() -> None:
        login_loop.quit()

    controller.accepted.connect(_accept)
    controller.rejected.connect(_reject)
    login_loop.exec()
    for root in engine.rootObjects():
        close = getattr(root, "close", None)
        if callable(close):
            close()
    return accepted["value"]


def main(argv: list[str] | None = None, desktop_api_registry: object | None = None) -> int:
    setup_logging()
    app = QApplication(argv or sys.argv)
    settings_store = AppSettingsStore()
    startup_theme, _startup_governance = _configure_runtime_environment(
        app,
        settings_store=settings_store,
    )
    services: dict[str, object] | None = None
    if desktop_api_registry is None:
        services = build_services()
        desktop_api_registry = services["desktop_api_registry"]
        skip_login = os.getenv("PM_SKIP_LOGIN", "0").strip().lower() in {"1", "true"}
        preauthenticated = bool(services["user_session"].is_authenticated())
        if (not skip_login or not preauthenticated) and not _prompt_for_login_qml(
            auth_service=services["auth_service"],
            user_session=services["user_session"],
        ):
            return 0

    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    if services is not None:
        principal = services["user_session"].principal
        update_shell_runtime_state(
            shell_context,
            theme_mode=startup_theme,
            user_display_name=principal.display_name or principal.username if principal else "",
        )
    else:
        update_shell_runtime_state(shell_context, theme_mode=startup_theme)
    platform_workspace_catalog = PlatformWorkspaceCatalog(
        getattr(desktop_api_registry, "platform_runtime", None) if desktop_api_registry is not None else None,
        desktop_api_registry=desktop_api_registry,
    )
    pm_workspace_catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    inventory_workspace_catalog = InventoryProcurementWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    maintenance_workspace_catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    engine = create_qml_engine()
    load_qml(
        engine,
        registry.get("shell.app").qml_path,
        initial_properties={
            "shellModel": shell_context,
            "platformCatalog": platform_workspace_catalog,
            "pmCatalog": pm_workspace_catalog,
            "inventoryCatalog": inventory_workspace_catalog,
            "maintenanceCatalog": maintenance_workspace_catalog,
        },
    )
    return app.exec()


__all__ = ["main"]
