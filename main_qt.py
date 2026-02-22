# main_qt.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from infra.resource import resource_path

from infra.db.base import SessionLocal
from infra.db.repositories import (
    SqlAlchemyProjectRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyCalendarEventRepository,
    SqlAlchemyWorkingCalendarRepository,
    SqlAlchemyBaselineRepository,
    SqlAlchemyProjectResourceRepository
)

from core.services.project_service import ProjectService
from core.services.task_service import TaskService
from core.services.resource_service import ResourceService
from core.services.project_calendar_service import CalendarService
from core.services.cost_service import CostService
from core.services.work_calendar_engine import WorkCalendarEngine
from core.services.work_calendar_service import WorkCalendarService
from core.services.scheduling_service import SchedulingEngine
from core.services.reporting_service import ReportingService
from core.services.dashboard_service import DashboardService
from core.services.baseline_service import BaselineService
from core.services.project_resource_service import ProjectResourceService

from infra.logging_config import setup_logging

from ui.main_window import MainWindow


def build_services():
    # same DB as CLI
    from infra.migrate import run_migrations
    from infra.path import default_db_path
    from pathlib import Path

    db_url:Path = default_db_path()

    run_migrations(
        db_url=db_url.as_posix()
    )
    #Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    project_repo = SqlAlchemyProjectRepository(session)
    task_repo = SqlAlchemyTaskRepository(session)
    resource_repo = SqlAlchemyResourceRepository(session)
    assignment_repo = SqlAlchemyAssignmentRepository(session)
    dependency_repo = SqlAlchemyDependencyRepository(session)
    cost_repo = SqlAlchemyCostRepository(session)
    calendar_repo = SqlAlchemyCalendarEventRepository(session)
    work_calendar_repo = SqlAlchemyWorkingCalendarRepository(session)
    baseline_repo =  SqlAlchemyBaselineRepository(session)
    project_resource_repo = SqlAlchemyProjectResourceRepository(session)
    
    work_calendar_engine = WorkCalendarEngine(work_calendar_repo, calendar_id="default")

    project_service = ProjectService(
        session,
        project_repo,
        task_repo,
        dependency_repo,
        assignment_repo,
        calendar_repo,
        cost_repo,
    )

    project_resource_service = ProjectResourceService(
        project_resource_repo=project_resource_repo,
        resource_repo=resource_repo,
        session=session
    )

    task_service = TaskService(
        session,
        task_repo,
        dependency_repo,
        assignment_repo,
        resource_repo,
        cost_repo,
        calendar_repo,
        work_calendar_engine,
        project_resource_repo,
        project_repo,
    )
    
    calendar_service = CalendarService(session, calendar_repo, task_repo)
    resource_service = ResourceService(session, resource_repo, assignment_repo, project_resource_repo)
    cost_service = CostService(session, cost_repo, project_repo, task_repo)
    work_calendar_service = WorkCalendarService(session, work_calendar_repo, work_calendar_engine)
    scheduling_engine = SchedulingEngine(session, task_repo, dependency_repo, work_calendar_engine)

    reporting_service = ReportingService(
        session,
        project_repo,
        task_repo,
        resource_repo,
        assignment_repo,
        cost_repo,
        scheduling_engine,
        work_calendar_engine,
        baseline_repo= baseline_repo,
        project_resource_repo= project_resource_repo
    )
    
    baseline_service = BaselineService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        cost_repo=cost_repo,
        baseline_repo=baseline_repo,
        scheduling=scheduling_engine,
        calendar=work_calendar_engine,
        resource_repo=resource_repo,
        project_resource_repo=project_resource_repo
    )
    
    return {
        "session": session,
        "project_service": project_service,
        "task_service": task_service,
        "calendar_service": calendar_service,
        "resource_service": resource_service,
        "cost_service": cost_service,
        "work_calendar_engine": work_calendar_engine,
        "work_calendar_service": work_calendar_service,
        "scheduling_engine": scheduling_engine,
        "reporting_service": reporting_service,
        "baseline_service": baseline_service,
        "project_resource_service": project_resource_service,
    }


def main():
    setup_logging()

    app = QApplication(sys.argv)
    icon_path = resource_path("assets/icons/app.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # 1) Global font (Segoe UI is modern & native on Windows, use Roboto/Noto on Linux etc.)
    app.setFont(QFont("Segoe UI", 9))

    # 2) Global stylesheet (QSS)
    from ui.styles.theme import apply_app_style
    apply_app_style(app)
   
    services = build_services()
    dashboard_service = DashboardService(
        reporting_service=services["reporting_service"],
        task_service=services["task_service"],
        project_service=services["project_service"],
        scheduling_engine=services["scheduling_engine"],
        work_calendar_engine=services["work_calendar_engine"],
    )
    services["dashboard_service"] = dashboard_service
    window = MainWindow(services)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()