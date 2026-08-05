import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    ProjectFinancialsWorkspacePresenter,
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.approval.models.approval import ApprovalRequestDto
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.domain.approval import ApprovalStatus
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.domain.master_data.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until
from src.ui_qml.modules.project_management.presenters.collaboration import (
    ProjectCollaborationWorkspacePresenter,
)


class _FakeFinancialCostService:
    def __init__(self, costs_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._costs_by_project = costs_by_project

    def list_cost_items_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._costs_by_project.get(project_id, []))


class _FakeFinanceDesktopService:
    def __init__(self, snapshots_by_project: dict[str, SimpleNamespace]) -> None:
        self._snapshots_by_project = snapshots_by_project

    def get_finance_snapshot(self, project_id: str) -> SimpleNamespace:
        return self._snapshots_by_project[project_id]


def _build_cost_record(
    *,
    cost_id: str,
    project_id: str,
    task_id: str | None,
    description: str,
    planned_amount: float,
    committed_amount: float,
    actual_amount: float,
    cost_type: CostType,
    incurred_date: date | None,
    currency_code: str | None,
    version: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=cost_id,
        project_id=project_id,
        task_id=task_id,
        description=description,
        planned_amount=planned_amount,
        committed_amount=committed_amount,
        actual_amount=actual_amount,
        cost_type=cost_type,
        incurred_date=incurred_date,
        currency_code=currency_code,
        version=version,
    )
