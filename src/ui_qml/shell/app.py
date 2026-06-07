from __future__ import annotations

import os
import sys
import logging
from time import perf_counter

from PySide6.QtCore import QEventLoop
from PySide6.QtGui import QFont, QGuiApplication, QIcon

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


logger = logging.getLogger(__name__)


def build_services() -> dict[str, object]:
    started = perf_counter()
    db_url = get_db_url()
    logger.info("Service build begin db_url=%s", db_url)
    migration_started = perf_counter()
    logger.info("Database migration step begin")
    try:
        run_migrations(db_url=db_url)
    except Exception:
        logger.exception("Database migration step failed")
        raise
    logger.info(
        "Database migrations complete duration_ms=%.1f",
        (perf_counter() - migration_started) * 1000,
    )
    session = SessionLocal()
    logger.info("Database session created session_class=%s", type(session).__name__)
    graph_started = perf_counter()
    services = build_service_dict(session)
    logger.info(
        "Service graph built service_count=%s duration_ms=%.1f",
        len(services),
        (perf_counter() - graph_started) * 1000,
    )
    desktop_api_registry = build_desktop_api_registry(services)
    services["desktop_api_registry"] = desktop_api_registry
    logger.info(
        "Desktop API registry ready duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return services


def _configure_runtime_environment(app: QGuiApplication, *, settings_store: AppSettingsStore) -> tuple[str, str]:
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
    log_file = setup_logging()
    logger.info("App startup begin argv_count=%s log_file=%s", len(argv or sys.argv), log_file)
    app = QGuiApplication(argv or sys.argv)
    settings_store = AppSettingsStore()
    startup_theme, _startup_governance = _configure_runtime_environment(
        app,
        settings_store=settings_store,
    )
    logger.info("Runtime environment configured theme=%s", startup_theme)
    services: dict[str, object] | None = None
    if desktop_api_registry is None:
        services = build_services()
        desktop_api_registry = services["desktop_api_registry"]
        skip_login = os.getenv("PM_SKIP_LOGIN", "0").strip().lower() in {"1", "true"}
        preauthenticated = bool(services["user_session"].is_authenticated())
        logger.info(
            "Authentication gate evaluated skip_login=%s preauthenticated=%s",
            skip_login,
            preauthenticated,
        )
        if (not skip_login or not preauthenticated) and not _prompt_for_login_qml(
            auth_service=services["auth_service"],
            user_session=services["user_session"],
        ):
            logger.info("Login rejected; exiting application before shell load.")
            return 0

    registry = build_qml_route_registry()
    routes = registry.list_routes()
    nav_routes = registry.list_navigation_routes()
    logger.info(
        "QML route registry built route_count=%s navigation_route_count=%s",
        len(routes),
        len(nav_routes),
    )
    shell_context = build_shell_context(build_main_window_navigation(registry))
    logger.info("Shell context created initial_route=%s", shell_context.currentRouteId)
    if services is not None:
        principal = services["user_session"].principal
        update_shell_runtime_state(
            shell_context,
            theme_mode=startup_theme,
            user_display_name=principal.display_name or principal.username if principal else "",
        )
        logger.info(
            "Shell runtime state updated authenticated=%s user_present=%s",
            services["user_session"].is_authenticated(),
            principal is not None,
        )
    else:
        update_shell_runtime_state(shell_context, theme_mode=startup_theme)
    logger.info("Creating workspace catalogs.")
    platform_workspace_catalog = PlatformWorkspaceCatalog(
        getattr(desktop_api_registry, "platform_runtime", None) if desktop_api_registry is not None else None,
        desktop_api_registry=desktop_api_registry,
    )
    logger.info("Platform workspace catalog created.")
    pm_workspace_catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    logger.info("Project Management workspace catalog created.")
    inventory_workspace_catalog = InventoryProcurementWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    logger.info("Inventory/Procurement workspace catalog created.")
    maintenance_workspace_catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=desktop_api_registry,
    )
    logger.info("Maintenance workspace catalog created.")
    engine = create_qml_engine()
    shell_route = registry.get("shell.app")
    logger.info("Loading shell QML path=%s", shell_route.qml_path)
    load_qml(
        engine,
        shell_route.qml_path,
        initial_properties={
            "shellModel": shell_context,
            "platformCatalog": platform_workspace_catalog,
            "pmCatalog": pm_workspace_catalog,
            "inventoryCatalog": inventory_workspace_catalog,
            "maintenanceCatalog": maintenance_workspace_catalog,
        },
    )
    logger.info("Shell QML loaded; entering Qt event loop.")
    app.setProperty("pmEventLoopRunning", True)
    try:
        return app.exec()
    finally:
        app.setProperty("pmEventLoopRunning", False)


__all__ = ["main"]
