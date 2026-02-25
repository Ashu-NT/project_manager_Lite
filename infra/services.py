from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from core.models import CostType, DependencyType
from core.services.approval import ApprovalService
from core.services.audit import AuditService
from core.services.baseline import BaselineService
from core.services.auth import AuthService
from core.services.auth.session import UserSessionContext
from core.services.calendar import CalendarService
from core.services.cost import CostService
from core.services.dashboard import DashboardService
from core.services.project import ProjectResourceService, ProjectService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.scheduling import SchedulingEngine
from core.services.task import TaskService
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from infra.db.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyBaselineRepository,
    SqlAlchemyCalendarEventRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyPermissionRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserRoleRepository,
    SqlAlchemyWorkingCalendarRepository,
)
from infra.db.repositories_approval import SqlAlchemyApprovalRepository
from infra.db.repositories_audit import SqlAlchemyAuditLogRepository


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Unsupported date value: {value!r}")


def _as_cost_type(value: Any) -> CostType:
    if isinstance(value, CostType):
        return value
    return CostType((value or CostType.OVERHEAD.value))


def _as_dependency_type(value: Any) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    return DependencyType((value or DependencyType.FINISH_TO_START.value))


@dataclass(frozen=True)
class ServiceGraph:
    session: Session
    user_session: UserSessionContext
    auth_service: AuthService
    audit_service: AuditService
    approval_service: ApprovalService
    project_service: ProjectService
    task_service: TaskService
    calendar_service: CalendarService
    resource_service: ResourceService
    cost_service: CostService
    work_calendar_engine: WorkCalendarEngine
    work_calendar_service: WorkCalendarService
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    project_resource_service: ProjectResourceService

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "user_session": self.user_session,
            "auth_service": self.auth_service,
            "audit_service": self.audit_service,
            "approval_service": self.approval_service,
            "project_service": self.project_service,
            "task_service": self.task_service,
            "calendar_service": self.calendar_service,
            "resource_service": self.resource_service,
            "cost_service": self.cost_service,
            "work_calendar_engine": self.work_calendar_engine,
            "work_calendar_service": self.work_calendar_service,
            "scheduling_engine": self.scheduling_engine,
            "reporting_service": self.reporting_service,
            "baseline_service": self.baseline_service,
            "dashboard_service": self.dashboard_service,
            "project_resource_service": self.project_resource_service,
        }


def build_service_graph(session: Session) -> ServiceGraph:
    user_session = UserSessionContext()
    project_repo = SqlAlchemyProjectRepository(session)
    task_repo = SqlAlchemyTaskRepository(session)
    resource_repo = SqlAlchemyResourceRepository(session)
    assignment_repo = SqlAlchemyAssignmentRepository(session)
    dependency_repo = SqlAlchemyDependencyRepository(session)
    cost_repo = SqlAlchemyCostRepository(session)
    calendar_repo = SqlAlchemyCalendarEventRepository(session)
    work_calendar_repo = SqlAlchemyWorkingCalendarRepository(session)
    baseline_repo = SqlAlchemyBaselineRepository(session)
    project_resource_repo = SqlAlchemyProjectResourceRepository(session)
    user_repo = SqlAlchemyUserRepository(session)
    role_repo = SqlAlchemyRoleRepository(session)
    permission_repo = SqlAlchemyPermissionRepository(session)
    user_role_repo = SqlAlchemyUserRoleRepository(session)
    role_permission_repo = SqlAlchemyRolePermissionRepository(session)
    audit_repo = SqlAlchemyAuditLogRepository(session)
    approval_repo = SqlAlchemyApprovalRepository(session)

    work_calendar_engine = WorkCalendarEngine(work_calendar_repo, calendar_id="default")
    audit_service = AuditService(
        session=session,
        audit_repo=audit_repo,
        user_session=user_session,
    )
    approval_service = ApprovalService(
        session=session,
        approval_repo=approval_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    auth_service = AuthService(
        session=session,
        user_repo=user_repo,
        role_repo=role_repo,
        permission_repo=permission_repo,
        user_role_repo=user_role_repo,
        role_permission_repo=role_permission_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    auth_service.bootstrap_defaults()

    project_service = ProjectService(
        session,
        project_repo,
        task_repo,
        dependency_repo,
        assignment_repo,
        calendar_repo,
        cost_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    project_resource_service = ProjectResourceService(
        project_resource_repo=project_resource_repo,
        resource_repo=resource_repo,
        session=session,
        user_session=user_session,
        audit_service=audit_service,
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
        user_session=user_session,
        audit_service=audit_service,
        approval_service=approval_service,
    )
    calendar_service = CalendarService(session, calendar_repo, task_repo)
    resource_service = ResourceService(
        session,
        resource_repo,
        assignment_repo,
        project_resource_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    cost_service = CostService(
        session,
        cost_repo,
        project_repo,
        task_repo,
        user_session=user_session,
        audit_service=audit_service,
        approval_service=approval_service,
    )
    work_calendar_service = WorkCalendarService(
        session,
        work_calendar_repo,
        work_calendar_engine,
        user_session=user_session,
    )
    scheduling_engine = SchedulingEngine(
        session,
        task_repo,
        dependency_repo,
        work_calendar_engine,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
    )
    reporting_service = ReportingService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        resource_repo=resource_repo,
        assignment_repo=assignment_repo,
        cost_repo=cost_repo,
        scheduling_engine=scheduling_engine,
        calendar=work_calendar_engine,
        baseline_repo=baseline_repo,
        project_resource_repo=project_resource_repo,
    )
    baseline_service = BaselineService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        cost_repo=cost_repo,
        baseline_repo=baseline_repo,
        scheduling=scheduling_engine,
        calendar=work_calendar_engine,
        project_resource_repo=project_resource_repo,
        resource_repo=resource_repo,
        user_session=user_session,
        audit_service=audit_service,
        approval_service=approval_service,
    )
    dashboard_service = DashboardService(
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        user_session=user_session,
    )
    approval_service.register_apply_handler(
        "baseline.create",
        lambda req: baseline_service.create_baseline(
            project_id=req.payload["project_id"],
            name=req.payload.get("name") or "Baseline",
            bypass_approval=True,
        ),
    )
    approval_service.register_apply_handler(
        "dependency.add",
        lambda req: task_service.add_dependency(
            predecessor_id=req.payload["predecessor_id"],
            successor_id=req.payload["successor_id"],
            dependency_type=_as_dependency_type(req.payload.get("dependency_type", "FS")),
            lag_days=int(req.payload.get("lag_days", 0) or 0),
            bypass_approval=True,
        ),
    )
    approval_service.register_apply_handler(
        "dependency.remove",
        lambda req: task_service.remove_dependency(
            dep_id=req.payload["dependency_id"],
            bypass_approval=True,
        ),
    )
    approval_service.register_apply_handler(
        "cost.add",
        lambda req: cost_service.add_cost_item(
            project_id=req.payload["project_id"],
            description=req.payload.get("description", ""),
            planned_amount=float(req.payload.get("planned_amount", 0.0) or 0.0),
            task_id=req.payload.get("task_id"),
            cost_type=_as_cost_type(req.payload.get("cost_type", "OVERHEAD")),
            committed_amount=float(req.payload.get("committed_amount", 0.0) or 0.0),
            actual_amount=float(req.payload.get("actual_amount", 0.0) or 0.0),
            incurred_date=_parse_date(req.payload.get("incurred_date")),
            currency_code=req.payload.get("currency_code"),
            bypass_approval=True,
        ),
    )
    approval_service.register_apply_handler(
        "cost.update",
        lambda req: cost_service.update_cost_item(
            cost_id=req.payload["cost_id"],
            description=req.payload.get("description"),
            planned_amount=req.payload.get("planned_amount"),
            committed_amount=req.payload.get("committed_amount"),
            actual_amount=req.payload.get("actual_amount"),
            cost_type=(
                _as_cost_type(req.payload.get("cost_type"))
                if req.payload.get("cost_type") is not None
                else None
            ),
            incurred_date=_parse_date(req.payload.get("incurred_date")),
            currency_code=req.payload.get("currency_code"),
            expected_version=req.payload.get("expected_version"),
            bypass_approval=True,
        ),
    )
    approval_service.register_apply_handler(
        "cost.delete",
        lambda req: cost_service.delete_cost_item(
            cost_id=req.payload["cost_id"],
            bypass_approval=True,
        ),
    )

    return ServiceGraph(
        session=session,
        user_session=user_session,
        auth_service=auth_service,
        audit_service=audit_service,
        approval_service=approval_service,
        project_service=project_service,
        task_service=task_service,
        calendar_service=calendar_service,
        resource_service=resource_service,
        cost_service=cost_service,
        work_calendar_engine=work_calendar_engine,
        work_calendar_service=work_calendar_service,
        scheduling_engine=scheduling_engine,
        reporting_service=reporting_service,
        baseline_service=baseline_service,
        dashboard_service=dashboard_service,
        project_resource_service=project_resource_service,
    )


def build_service_dict(session: Session) -> dict[str, Any]:
    return build_service_graph(session).as_dict()
