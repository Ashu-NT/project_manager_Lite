from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.auth import UserSessionContext
from src.core.modules.project_management.application.projects import ProjectService
from core.modules.project_management.services.scheduling import SchedulingEngine
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from ui.modules.project_management.calendar.calculator import CalendarCalculatorMixin
from ui.modules.project_management.calendar.holidays import CalendarHolidaysMixin
from ui.modules.project_management.calendar.project_ops import CalendarProjectOpsMixin
from ui.modules.project_management.calendar.surface import CalendarSurfaceMixin
from ui.modules.project_management.calendar.working_time import CalendarWorkingTimeMixin
from ui.modules.project_management.shared.domain_event_filters import is_project_management_domain_event
from src.ui.shared.widgets.guards import has_permission


class CalendarTab(
    CalendarSurfaceMixin,
    CalendarWorkingTimeMixin,
    CalendarHolidaysMixin,
    CalendarCalculatorMixin,
    CalendarProjectOpsMixin,
    QWidget,
):
    """
    Calendar tab coordinator:
    - builds widgets
    - delegates working-time/holiday/calculation/project actions to mixins
    """

    def __init__(
        self,
        work_calendar_service: WorkCalendarService,
        work_calendar_engine: WorkCalendarEngine,
        scheduling_engine: SchedulingEngine,
        project_service: ProjectService,
        task_service: TaskService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._wc_service: WorkCalendarService = work_calendar_service
        self._wc_engine: WorkCalendarEngine = work_calendar_engine
        self._scheduling_engine: SchedulingEngine = scheduling_engine
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._user_session = user_session
        self._can_manage_calendar = has_permission(self._user_session, "task.manage")

        self._setup_ui()
        self.load_calendar_config()
        self.load_holidays()
        self.reload_projects()
        domain_events.domain_changed.connect(self._on_domain_change)

    def _on_domain_change(self, event) -> None:
        if is_project_management_domain_event(event, "project"):
            self._on_project_changed(event.entity_id)
