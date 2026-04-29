from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.access import ScopedRolePolicy
from core.modules.project_management.domain.enums import CostType, DependencyType
from core.modules.project_management.access.policy import (
    PROJECT_SCOPE_ROLE_CHOICES,
    normalize_project_scope_role,
    resolve_project_scope_permissions,
)
from src.core.platform.time.application import TimeService
from core.modules.project_management.services.baseline import BaselineService
from core.modules.project_management.services.calendar import CalendarService
from core.modules.project_management.services.collaboration import CollaborationService
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.dashboard import DashboardService
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.import_service import DataImportService
from core.modules.project_management.services.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ProjectResourceService
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.scheduling import SchedulingEngine
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.timesheet import TimesheetService
from core.modules.project_management.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from infra.modules.project_management.collaboration_store import TaskCollaborationStore
from src.infra.composition.platform_registry import PlatformServiceBundle
from src.infra.composition.repositories import RepositoryBundle


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
class ProjectManagementServiceBundle:
    time_service: TimeService
    collaboration_service: CollaborationService
    project_service: ProjectService
    task_service: TaskService
    timesheet_service: TimesheetService
    calendar_service: CalendarService
    resource_service: ResourceService
    cost_service: CostService
    finance_service: FinanceService
    work_calendar_engine: WorkCalendarEngine
    work_calendar_service: WorkCalendarService
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    portfolio_service: PortfolioService
    register_service: RegisterService
    project_resource_service: ProjectResourceService
    data_import_service: DataImportService
    task_collaboration_store: TaskCollaborationStore


def build_project_management_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
) -> ProjectManagementServiceBundle:
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="project",
            role_choices=PROJECT_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_project_scope_role,
            resolve_permissions=resolve_project_scope_permissions,
        )
    )
    platform_services.access_service.register_scope_exists_resolver(
        "project",
        lambda project_id: repositories.project_repo.get(project_id) is not None,
    )
    work_calendar_engine = WorkCalendarEngine(repositories.work_calendar_repo, calendar_id="default")
    project_service = ProjectService(
        session,
        repositories.project_repo,
        repositories.task_repo,
        repositories.dependency_repo,
        repositories.assignment_repo,
        repositories.time_entry_repo,
        repositories.calendar_repo,
        repositories.cost_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    timesheet_service = TimesheetService(
        session=session,
        assignment_repo=repositories.assignment_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        employee_repo=repositories.employee_repo,
        time_entry_repo=repositories.time_entry_repo,
        timesheet_period_repo=repositories.timesheet_period_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    time_service: TimeService = timesheet_service
    project_resource_service = ProjectResourceService(
        project_resource_repo=repositories.project_resource_repo,
        resource_repo=repositories.resource_repo,
        session=session,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    register_service = RegisterService(
        session=session,
        project_repo=repositories.project_repo,
        register_repo=repositories.register_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        repositories.task_repo,
        repositories.dependency_repo,
        work_calendar_engine,
        assignment_repo=repositories.assignment_repo,
        resource_repo=repositories.resource_repo,
    )
    task_service = TaskService(
        session,
        repositories.task_repo,
        repositories.dependency_repo,
        repositories.assignment_repo,
        repositories.time_entry_repo,
        repositories.timesheet_period_repo,
        timesheet_service,
        repositories.resource_repo,
        repositories.cost_repo,
        repositories.calendar_repo,
        work_calendar_engine,
        scheduling_engine,
        repositories.project_resource_repo,
        repositories.project_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    calendar_service = CalendarService(
        session,
        repositories.calendar_repo,
        repositories.task_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    resource_service = ResourceService(
        session,
        repositories.resource_repo,
        repositories.assignment_repo,
        repositories.project_resource_repo,
        repositories.time_entry_repo,
        repositories.employee_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    cost_service = CostService(
        session,
        repositories.cost_repo,
        repositories.project_repo,
        repositories.task_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    work_calendar_service = WorkCalendarService(
        session,
        repositories.work_calendar_repo,
        work_calendar_engine,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    reporting_service = ReportingService(
        session=session,
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        assignment_repo=repositories.assignment_repo,
        cost_repo=repositories.cost_repo,
        scheduling_engine=scheduling_engine,
        calendar=work_calendar_engine,
        baseline_repo=repositories.baseline_repo,
        project_resource_repo=repositories.project_resource_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    finance_service = FinanceService(
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        cost_repo=repositories.cost_repo,
        project_resource_repo=repositories.project_resource_repo,
        reporting_service=reporting_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    collaboration_service = CollaborationService(
        session=session,
        comment_repo=repositories.task_comment_repo,
        presence_repo=repositories.task_presence_repo,
        task_repo=repositories.task_repo,
        project_repo=repositories.project_repo,
        user_repo=repositories.user_repo,
        audit_repo=repositories.audit_repo,
        project_membership_repo=repositories.project_membership_repo,
        document_integration_service=platform_services.document_integration_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    portfolio_service = PortfolioService(
        session=session,
        intake_repo=repositories.portfolio_intake_repo,
        dependency_repo=repositories.portfolio_project_dependency_repo,
        scoring_template_repo=repositories.portfolio_scoring_template_repo,
        scenario_repo=repositories.portfolio_scenario_repo,
        audit_repo=repositories.audit_repo,
        project_repo=repositories.project_repo,
        resource_repo=repositories.resource_repo,
        reporting_service=reporting_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    baseline_service = BaselineService(
        session=session,
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        cost_repo=repositories.cost_repo,
        baseline_repo=repositories.baseline_repo,
        scheduling=scheduling_engine,
        calendar=work_calendar_engine,
        project_resource_repo=repositories.project_resource_repo,
        resource_repo=repositories.resource_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    dashboard_service = DashboardService(
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        register_service=register_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    data_import_service = DataImportService(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        cost_service=cost_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
    )
    task_collaboration_store = TaskCollaborationStore(session_factory=lambda: session)
    _register_project_management_approval_handlers(
        approval_service=platform_services.approval_service,
        baseline_service=baseline_service,
        task_service=task_service,
        cost_service=cost_service,
    )
    return ProjectManagementServiceBundle(
        time_service=time_service,
        collaboration_service=collaboration_service,
        project_service=project_service,
        task_service=task_service,
        timesheet_service=timesheet_service,
        calendar_service=calendar_service,
        resource_service=resource_service,
        cost_service=cost_service,
        finance_service=finance_service,
        work_calendar_engine=work_calendar_engine,
        work_calendar_service=work_calendar_service,
        scheduling_engine=scheduling_engine,
        reporting_service=reporting_service,
        baseline_service=baseline_service,
        dashboard_service=dashboard_service,
        portfolio_service=portfolio_service,
        register_service=register_service,
        project_resource_service=project_resource_service,
        data_import_service=data_import_service,
        task_collaboration_store=task_collaboration_store,
    )


def _register_project_management_approval_handlers(
    *,
    approval_service,
    baseline_service: BaselineService,
    task_service: TaskService,
    cost_service: CostService,
) -> None:
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


__all__ = ["ProjectManagementServiceBundle", "build_project_management_service_bundle"]
