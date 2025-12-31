# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infra.db.base import Base
from infra.db.repositories import (
    SqlAlchemyProjectRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyCalendarEventRepository,
    SqlAlchemyWorkingCalendarRepository,
    SqlAlchemyProjectResourceRepository,
)

from core.services.project_service import ProjectService
from core.services.task_service import TaskService
from core.services.resource_service import ResourceService
from core.services.project_calendar_service import CalendarService
from core.services.cost_service import CostService
from core.services.work_calendar_engine import WorkCalendarEngine
from core.services.work_calendar_service import WorkCalendarService
from core.services.scheduling_service import SchedulingEngine


@pytest.fixture
def session():
    # separate in-memory DB for tests
    engine = create_engine("sqlite:///:memory:", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def services(session):
    # Recreate what build_services() does, but with the test session
    project_repo = SqlAlchemyProjectRepository(session)
    task_repo = SqlAlchemyTaskRepository(session)
    resource_repo = SqlAlchemyResourceRepository(session)
    assignment_repo = SqlAlchemyAssignmentRepository(session)
    dependency_repo = SqlAlchemyDependencyRepository(session)
    cost_repo = SqlAlchemyCostRepository(session)
    calendar_repo = SqlAlchemyCalendarEventRepository(session)
    work_calendar_repo = SqlAlchemyWorkingCalendarRepository(session)
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
    )
    calendar_service = CalendarService(session, calendar_repo, task_repo)
    resource_service = ResourceService(session, resource_repo, assignment_repo)
    cost_service = CostService(session, cost_repo, project_repo, task_repo)
    work_calendar_service = WorkCalendarService(session, work_calendar_repo, work_calendar_engine)
    scheduling_engine = SchedulingEngine(session, task_repo, dependency_repo, work_calendar_engine)

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
    }