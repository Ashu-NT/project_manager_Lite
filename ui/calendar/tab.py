from __future__ import annotations

from PySide6.QtWidgets import QWidget

from core.events.domain_events import domain_events
from core.services.auth import UserSessionContext
from core.services.project import ProjectService
from core.services.scheduling import SchedulingEngine
from core.services.task import TaskService
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from ui.calendar.calculator import CalendarCalculatorMixin
from ui.calendar.holidays import CalendarHolidaysMixin
from ui.calendar.project_ops import CalendarProjectOpsMixin
from ui.calendar.surface import CalendarSurfaceMixin
from ui.calendar.working_time import CalendarWorkingTimeMixin
from ui.shared.guards import has_permission


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
        domain_events.project_changed.connect(self._on_project_changed)
