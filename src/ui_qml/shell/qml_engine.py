from __future__ import annotations

from pathlib import Path
from typing import Any
from PySide6.QtQml import QQmlApplicationEngine

import src.ui_qml.shell.context  # noqa: F401
import src.ui_qml.shell.login  # noqa: F401
import src.ui_qml.platform.context  # noqa: F401
import src.ui_qml.platform.controllers.common.workspace_controller_base  # noqa: F401
import src.ui_qml.platform.controllers.admin.admin_console_controller  # noqa: F401
import src.ui_qml.platform.controllers.admin.access_workspace_controller  # noqa: F401
import src.ui_qml.platform.controllers.admin.support_workspace_controller  # noqa: F401
import src.ui_qml.platform.controllers.control.control_workspace_controller  # noqa: F401
import src.ui_qml.platform.controllers.settings.settings_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.context  # noqa: F401
import src.ui_qml.modules.project_management.controllers.common.workspace_controller_base  # noqa: F401
import src.ui_qml.modules.project_management.controllers.projects.projects_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.collaboration.collaboration_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.financials.financials_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.portfolio.portfolio_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.scheduling.scheduling_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.tasks.tasks_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.resources.resources_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.register.register_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.dashboard.dashboard_workspace_controller  # noqa: F401
import src.ui_qml.modules.project_management.controllers.timesheets.timesheets_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.context  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.common.workspace_controller_base  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.assets.assets_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.dashboard.dashboard_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.planner.planner_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.preventive.preventive_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.reliability.reliability_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.work_orders.work_orders_workspace_controller  # noqa: F401
import src.ui_qml.modules.maintenance.controllers.work_requests.work_requests_workspace_controller  # noqa: F401
import src.ui_qml.modules.inventory_procurement.context  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.common.workspace_controller_base  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.catalog.catalog_workspace_controller  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.dashboard.dashboard_workspace_controller  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.inventory.inventory_workspace_controller  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.pricing.pricing_workspace_controller  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.procurement.procurement_workspace_controller  # noqa: F401
import src.ui_qml.modules.inventory_procurement.controllers.reservations.reservations_workspace_controller  # noqa: F401

UI_QML_ROOT = Path(__file__).resolve().parents[1]
QML_IMPORT_ROOTS = (
    UI_QML_ROOT / "shared" / "qml",
    UI_QML_ROOT / "shell" / "qml",
    UI_QML_ROOT / "platform" / "qml",
    *(path for path in (UI_QML_ROOT / "modules").glob("*/qml")),
)


def create_qml_engine() -> QQmlApplicationEngine:
    engine = QQmlApplicationEngine()
    for import_root in QML_IMPORT_ROOTS:
        if import_root.exists():
            engine.addImportPath(str(import_root))
    return engine


def expose_context_property(engine: QQmlApplicationEngine, name: str, value: Any) -> None:
    engine.rootContext().setContextProperty(name, value)


def load_qml(
    engine: QQmlApplicationEngine,
    qml_path: Path,
    *,
    initial_properties: dict[str, Any] | None = None,
) -> None:
    if initial_properties is not None:
        engine.setInitialProperties(initial_properties)
    engine.load(str(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML root: {qml_path}")


__all__ = ["create_qml_engine", "expose_context_property", "load_qml"]
