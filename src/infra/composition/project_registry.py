from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

import logging
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.access import ScopedRolePolicy
from src.core.platform.approval.contracts import (
    ApprovalHandlerResult,
    ApprovalPostCommitEvent,
)
from src.core.modules.project_management.domain.enums import CostType, DependencyType
from src.core.modules.project_management.access.policy import (
    PROJECT_SCOPE_ROLE_CHOICES,
    normalize_project_scope_role,
    resolve_project_scope_permissions,
)
from src.core.platform.time.application import TimeService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import CostService, FinanceService
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.infrastructure.importers import DataImportService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.application.collaboration import CollaborationService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import ProjectCalendarAdapter
from src.core.modules.project_management.application.resources.enterprise_resource_availability import EnterpriseResourceAvailabilityService
from src.core.modules.project_management.application.resources.resource_capacity_calculator import ResourceCapacityCalculator
from src.infra.composition.platform_registry import PlatformServiceBundle
from src.infra.composition.repositories import RepositoryBundle


logger = logging.getLogger(__name__)


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
    resource_service: ResourceService
    cost_service: CostService
    finance_service: FinanceService
    work_calendar_engine: CalendarProtocol  # GlobalCalendarShim — enterprise-backed
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    portfolio_service: PortfolioService
    register_service: RegisterService
    project_resource_service: ProjectResourceService
    data_import_service: DataImportService
    assignment_skill_validator: AssignmentSkillValidator
    project_calendar_adapter: ProjectCalendarAdapter
    enterprise_resource_availability: EnterpriseResourceAvailabilityService
    resource_capacity_calculator: ResourceCapacityCalculator


def build_project_management_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
) -> ProjectManagementServiceBundle:
    started = perf_counter()
    logger.debug("Project Management service bundle build begin")
    logger.debug("Project Management platform registrations begin")
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="project",
            role_choices=PROJECT_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_project_scope_role,
            resolve_permissions=resolve_project_scope_permissions,
        )
    )
    def _project_belongs_to_tenant(tenant_id: str, project_id: str) -> bool:
        return (
            platform_services.tenant_context_service.require_active_tenant_id(
                operation_label="validate project access scope"
            )
            == tenant_id
            and repositories.project_repo.get(project_id) is not None
        )

    platform_services.access_service.register_scope_exists_resolver(
        "project",
        _project_belongs_to_tenant,
    )
    platform_services.role_governance_service.register_scope_exists_resolver(
        "project",
        _project_belongs_to_tenant,
    )
    platform_services.auth_service.register_canonical_scope_tenant_resolver(
        "project",
        _project_belongs_to_tenant,
    )
    logger.debug("Project Management platform registrations complete")
    logger.debug("Project Management core services build begin")
    # GlobalCalendarShim is the enterprise-backed calendar. Used everywhere WorkCalendarEngine was.
    work_calendar_engine = platform_services.global_calendar_shim
    project_service = ProjectService(
        session,
        repositories.project_repo,
        repositories.task_repo,
        repositories.dependency_repo,
        repositories.assignment_repo,
        repositories.time_entry_repo,
        repositories.cost_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_runtime_service,
        tenant_context_service=platform_services.tenant_context_service,
    )

    def _time_scope_organization_id(scope_type: str, scope_id: str) -> str | None:
        normalized_scope_type = str(scope_type or "").strip().lower()
        normalized_scope_id = str(scope_id or "").strip()
        if not normalized_scope_id:
            return None
        if normalized_scope_type == "project":
            project = repositories.project_repo.get(normalized_scope_id)
            return getattr(project, "organization_id", None) if project is not None else None
        if normalized_scope_type == "site":
            site = platform_services.site_repo.get(normalized_scope_id)
            return getattr(site, "organization_id", None) if site is not None else None
        return None

    timesheet_service = TimesheetService(
        session=session,
        assignment_repo=repositories.assignment_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        employee_repo=repositories.employee_repo,
        time_entry_repo=repositories.time_entry_repo,
        timesheet_period_repo=repositories.timesheet_period_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_runtime_service,
        tenant_context_service=platform_services.tenant_context_service,
        scope_organization_resolver=_time_scope_organization_id,
    )
    time_service: TimeService = timesheet_service
    project_resource_service = ProjectResourceService(
        project_resource_repo=repositories.project_resource_repo,
        resource_repo=repositories.resource_repo,
        session=session,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    register_service = RegisterService(
        session=session,
        project_repo=repositories.project_repo,
        register_repo=repositories.register_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_runtime_service,
    )
    # Build enterprise calendar adapter here so it can be injected into SchedulingEngine.
    # Instantiated before scheduling_engine so we pass it in during construction.
    _pre_project_calendar_adapter = ProjectCalendarAdapter(
        resolver=platform_services.enterprise_calendar_resolver,
        assignment_service=platform_services.calendar_assignment_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        repositories.task_repo,
        repositories.dependency_repo,
        platform_services.global_calendar_shim,  # enterprise global as base calendar
        assignment_repo=repositories.assignment_repo,
        resource_repo=repositories.resource_repo,
        project_calendar_adapter=_pre_project_calendar_adapter,
    )
    logger.debug("Project Management scheduling foundation built")
    assignment_skill_validator = AssignmentSkillValidator(
        skill_repo=repositories.resource_skill_repo,
        cert_repo=repositories.resource_cert_repo,
        requirement_repo=repositories.task_skill_req_repo,
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
        work_calendar_engine,
        scheduling_engine,
        repositories.project_resource_repo,
        repositories.project_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_runtime_service,
        notification_service=platform_services.notification_service,
        employee_repo=repositories.employee_repo,
        assignment_skill_validator=assignment_skill_validator,
    )
    resource_service = ResourceService(
        session,
        repositories.resource_repo,
        repositories.assignment_repo,
        repositories.project_resource_repo,
        repositories.time_entry_repo,
        repositories.employee_repo,
        skill_repo=repositories.resource_skill_repo,
        cert_repo=repositories.resource_cert_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_runtime_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    cost_service = CostService(
        session,
        repositories.cost_repo,
        repositories.project_repo,
        repositories.task_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        enterprise_audit_service=platform_services.enterprise_audit_service,
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
        calendar=platform_services.global_calendar_shim,
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
        assignment_repo=repositories.assignment_repo,
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
        audit_repo=repositories.audit_entry_repo,
        document_integration_service=platform_services.document_integration_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
        tenant_context_service=platform_services.tenant_context_service,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        notification_service=platform_services.notification_service,
    )
    portfolio_service = PortfolioService(
        session=session,
        intake_repo=repositories.portfolio_intake_repo,
        dependency_repo=repositories.portfolio_project_dependency_repo,
        scoring_template_repo=repositories.portfolio_scoring_template_repo,
        scenario_repo=repositories.portfolio_scenario_repo,
        audit_repo=repositories.audit_entry_repo,
        project_repo=repositories.project_repo,
        resource_repo=repositories.resource_repo,
        reporting_service=reporting_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_runtime_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    baseline_service = BaselineService(
        session=session,
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        cost_repo=repositories.cost_repo,
        baseline_repo=repositories.baseline_repo,
        scheduling=scheduling_engine,
        calendar=platform_services.global_calendar_shim,
        project_resource_repo=repositories.project_resource_repo,
        resource_repo=repositories.resource_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
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
        work_calendar_engine=platform_services.global_calendar_shim,
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
    project_calendar_adapter = _pre_project_calendar_adapter  # reuse the instance wired into SchedulingEngine
    enterprise_resource_availability = EnterpriseResourceAvailabilityService(
        resolver=platform_services.enterprise_calendar_resolver,
        resource_repo=repositories.resource_repo,
    )
    resource_capacity_calculator = ResourceCapacityCalculator(
        availability_service=enterprise_resource_availability,
    )
    logger.debug("Project Management core services built")
    _register_project_management_approval_handlers(
        approval_service=platform_services.approval_service,
        baseline_service=baseline_service,
        task_service=task_service,
        cost_service=cost_service,
    )
    logger.debug("Project Management approval handlers registered")
    logger.debug(
        "Project Management service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return ProjectManagementServiceBundle(
        time_service=time_service,
        collaboration_service=collaboration_service,
        project_service=project_service,
        task_service=task_service,
        timesheet_service=timesheet_service,
        resource_service=resource_service,
        cost_service=cost_service,
        finance_service=finance_service,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        reporting_service=reporting_service,
        baseline_service=baseline_service,
        dashboard_service=dashboard_service,
        portfolio_service=portfolio_service,
        register_service=register_service,
        project_resource_service=project_resource_service,
        data_import_service=data_import_service,
        assignment_skill_validator=assignment_skill_validator,
        project_calendar_adapter=project_calendar_adapter,
        enterprise_resource_availability=enterprise_resource_availability,
        resource_capacity_calculator=resource_capacity_calculator,
    )


def _register_project_management_approval_handlers(
    *,
    approval_service,
    baseline_service: BaselineService,
    task_service: TaskService,
    cost_service: CostService,
) -> None:
    # TRANSITION(PF-A0-UOW-BRIDGE): These handlers stage legacy service writes with
    # commit=False/bypass_approval=True. Remove both switches at the Phase C command cutover.
    def _result(signal_name: str, payload: str) -> ApprovalHandlerResult:
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent(signal_name, payload),)
        )

    def _apply_baseline(req) -> ApprovalHandlerResult:
        project_id = req.payload["project_id"]
        baseline_service.create_baseline(
            project_id=project_id,
            name=req.payload.get("name") or "Baseline",
            bypass_approval=True,
            commit=False,
        )
        return _result("baseline_changed", project_id)

    def _apply_dependency_add(req) -> ApprovalHandlerResult:
        task_service.add_dependency(
            predecessor_id=req.payload["predecessor_id"],
            successor_id=req.payload["successor_id"],
            dependency_type=_as_dependency_type(req.payload.get("dependency_type", "FS")),
            lag_days=int(req.payload.get("lag_days", 0) or 0),
            bypass_approval=True,
            commit=False,
        )
        return _result("tasks_changed", req.project_id or "")

    def _apply_dependency_remove(req) -> ApprovalHandlerResult:
        task_service.remove_dependency(
            dep_id=req.payload["dependency_id"],
            bypass_approval=True,
            commit=False,
        )
        return _result("tasks_changed", req.project_id or "")

    def _apply_cost_add(req) -> ApprovalHandlerResult:
        project_id = req.payload["project_id"]
        cost_service.add_cost_item(
            project_id=project_id,
            description=req.payload.get("description", ""),
            planned_amount=float(req.payload.get("planned_amount", 0.0) or 0.0),
            task_id=req.payload.get("task_id"),
            cost_type=_as_cost_type(req.payload.get("cost_type", "OVERHEAD")),
            committed_amount=float(req.payload.get("committed_amount", 0.0) or 0.0),
            actual_amount=float(req.payload.get("actual_amount", 0.0) or 0.0),
            incurred_date=_parse_date(req.payload.get("incurred_date")),
            currency_code=req.payload.get("currency_code"),
            code=req.payload.get("code", ""),
            bypass_approval=True,
            commit=False,
            approval_request_id=req.id,
        )
        return _result("costs_changed", project_id)

    def _apply_cost_update(req) -> ApprovalHandlerResult:
        cost_service.update_cost_item(
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
            code=req.payload.get("code"),
            bypass_approval=True,
            commit=False,
            approval_request_id=req.id,
        )
        return _result("costs_changed", req.project_id or "")

    def _apply_cost_delete(req) -> ApprovalHandlerResult:
        cost_service.delete_cost_item(
            cost_id=req.payload["cost_id"],
            bypass_approval=True,
            commit=False,
            approval_request_id=req.id,
        )
        return _result("costs_changed", req.project_id or "")

    approval_service.register_apply_handler(
        "baseline.create",
        _apply_baseline,
    )
    approval_service.register_apply_handler(
        "dependency.add",
        _apply_dependency_add,
    )
    approval_service.register_apply_handler(
        "dependency.remove",
        _apply_dependency_remove,
    )
    approval_service.register_apply_handler(
        "cost.add",
        _apply_cost_add,
    )
    approval_service.register_apply_handler(
        "cost.update",
        _apply_cost_update,
    )
    approval_service.register_apply_handler(
        "cost.delete",
        _apply_cost_delete,
    )


__all__ = ["ProjectManagementServiceBundle", "build_project_management_service_bundle"]
