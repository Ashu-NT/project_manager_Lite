from __future__ import annotations

from PySide6.QtWidgets import QWidget

from core.platform.notifications.domain_events import domain_events
from core.platform.auth import UserSessionContext
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.project import ProjectService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.task import TaskService
from ui.modules.project_management.report.actions import ReportActionsMixin
from ui.modules.project_management.report.project_flow import ReportProjectFlowMixin
from ui.modules.project_management.report.surface import ReportSurfaceMixin


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
        domain_events.project_changed.connect(self._on_project_changed_event)
