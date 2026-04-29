from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.auth import UserSessionContext
from src.core.modules.project_management.application.financials import FinanceService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.application.tasks import TaskService
from ui.modules.project_management.report.actions import ReportActionsMixin
from ui.modules.project_management.report.project_flow import ReportProjectFlowMixin
from ui.modules.project_management.report.surface import ReportSurfaceMixin
from ui.modules.project_management.shared.domain_event_filters import is_project_management_domain_event


class ReportTab(ReportSurfaceMixin, ReportProjectFlowMixin, ReportActionsMixin, QWidget):
    """Report tab coordinator: UI layout and event wiring only."""

    def __init__(
        self,
        project_service: ProjectService,
        reporting_service: ReportingService,
        task_service: TaskService | None = None,
        finance_service: FinanceService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._reporting_service: ReportingService = reporting_service
        self._task_service: TaskService | None = task_service
        self._finance_service: FinanceService | None = finance_service
        self._user_session = user_session
        self._setup_ui()
        self._load_projects()
        domain_events.domain_changed.connect(self._on_domain_change)

    def _on_domain_change(self, event) -> None:
        if is_project_management_domain_event(event, "project"):
            self._on_project_changed_event(event.entity_id)
