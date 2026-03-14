from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from application.platform import PlatformRuntimeApplicationService
from core.platform.common.models import CostType, DependencyType
from core.platform import (
    DEFAULT_ENTERPRISE_MODULES,
    ModuleCatalogService,
    ModuleRuntimeService,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
)
from core.platform.access import AccessControlService
from core.platform.approval import ApprovalService
from core.platform.audit import AuditService
from core.platform.auth import AuthService
from core.platform.auth.session import UserSessionContext
from core.platform.org import EmployeeService, OrganizationService
from core.platform.time import TimeService
from core.modules.project_management.services.baseline import BaselineService
from core.modules.project_management.services.calendar import CalendarService
from core.modules.project_management.services.collaboration import CollaborationService
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.dashboard import DashboardService
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.import_service import DataImportService
from core.modules.project_management.services.portfolio import PortfolioService
from core.modules.project_management.services.project import ProjectResourceService, ProjectService
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.scheduling import SchedulingEngine
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.timesheet import TimesheetService
from core.modules.project_management.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from infra.modules.project_management.collaboration_store import TaskCollaborationStore
from infra.platform.db.repositories import (
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
    SqlAlchemyEmployeeRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyModuleEntitlementRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTimeEntryRepository,
    SqlAlchemyTimesheetPeriodRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserRoleRepository,
    SqlAlchemyWorkingCalendarRepository,
)
from infra.platform.db.access import SqlAlchemyProjectMembershipRepository
from infra.platform.db.repositories_approval import SqlAlchemyApprovalRepository
from infra.platform.db.repositories_audit import SqlAlchemyAuditLogRepository
from infra.modules.project_management.db.collaboration import SqlAlchemyTaskCommentRepository
from infra.modules.project_management.db.portfolio import (
    SqlAlchemyPortfolioIntakeRepository,
    SqlAlchemyPortfolioScenarioRepository,
)
from infra.modules.project_management.db.repositories_register import SqlAlchemyRegisterEntryRepository


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
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_runtime_service: ModuleRuntimeService
    module_catalog_service: ModuleCatalogService
    time_service: TimeService
    auth_service: AuthService
    organization_service: OrganizationService
    employee_service: EmployeeService
    access_service: AccessControlService
    audit_service: AuditService
    approval_service: ApprovalService
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "user_session": self.user_session,
            "platform_runtime_application_service": self.platform_runtime_application_service,
            "module_runtime_service": self.module_runtime_service,
            "module_catalog_service": self.module_catalog_service,
            "time_service": self.time_service,
            "auth_service": self.auth_service,
            "organization_service": self.organization_service,
            "employee_service": self.employee_service,
            "access_service": self.access_service,
            "audit_service": self.audit_service,
            "approval_service": self.approval_service,
            "collaboration_service": self.collaboration_service,
            "project_service": self.project_service,
            "task_service": self.task_service,
            "timesheet_service": self.timesheet_service,
            "calendar_service": self.calendar_service,
            "resource_service": self.resource_service,
            "cost_service": self.cost_service,
            "finance_service": self.finance_service,
            "work_calendar_engine": self.work_calendar_engine,
            "work_calendar_service": self.work_calendar_service,
            "scheduling_engine": self.scheduling_engine,
            "reporting_service": self.reporting_service,
            "baseline_service": self.baseline_service,
            "dashboard_service": self.dashboard_service,
            "portfolio_service": self.portfolio_service,
            "register_service": self.register_service,
            "project_resource_service": self.project_resource_service,
            "data_import_service": self.data_import_service,
            "task_collaboration_store": self.task_collaboration_store,
        }


def build_service_graph(session: Session) -> ServiceGraph:
    user_session = UserSessionContext()
    project_repo = SqlAlchemyProjectRepository(session)
    task_repo = SqlAlchemyTaskRepository(session)
    resource_repo = SqlAlchemyResourceRepository(session)
    employee_repo = SqlAlchemyEmployeeRepository(session)
    organization_repo = SqlAlchemyOrganizationRepository(session)
    assignment_repo = SqlAlchemyAssignmentRepository(session)
    time_entry_repo = SqlAlchemyTimeEntryRepository(session)
    timesheet_period_repo = SqlAlchemyTimesheetPeriodRepository(session)
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
    project_membership_repo = SqlAlchemyProjectMembershipRepository(session)
    audit_repo = SqlAlchemyAuditLogRepository(session)
    approval_repo = SqlAlchemyApprovalRepository(session)
    register_repo = SqlAlchemyRegisterEntryRepository(session)
    task_comment_repo = SqlAlchemyTaskCommentRepository(session)
    portfolio_intake_repo = SqlAlchemyPortfolioIntakeRepository(session)
    portfolio_scenario_repo = SqlAlchemyPortfolioScenarioRepository(session)

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
        project_membership_repo=project_membership_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    auth_service.bootstrap_defaults()
    organization_service = OrganizationService(
        session=session,
        organization_repo=organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    organization_service.bootstrap_defaults()

    def _active_organization():
        return organization_repo.get_active()

    def _active_organization_id() -> str | None:
        organization = _active_organization()
        return organization.id if organization is not None else None

    module_entitlement_repo = SqlAlchemyModuleEntitlementRepository(
        session,
        organization_id_provider=_active_organization_id,
    )
    module_catalog_service = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(os.getenv("PM_ENABLED_MODULES")),
        licensed_codes=parse_licensed_module_codes(
            os.getenv("PM_LICENSED_MODULES")
            if os.getenv("PM_LICENSED_MODULES") is not None
            else os.getenv("PM_ENABLED_MODULES")
        ),
        entitlement_repo=module_entitlement_repo,
        session=session,
        user_session=user_session,
        audit_service=audit_service,
        organization_context_provider=_active_organization,
    )
    module_catalog_service.bootstrap_defaults()
    module_runtime_service = ModuleRuntimeService(module_catalog_service)
    platform_runtime_application_service = PlatformRuntimeApplicationService(
        module_runtime_service=module_runtime_service,
        organization_service=organization_service,
    )
    access_service = AccessControlService(
        session=session,
        membership_repo=project_membership_repo,
        project_repo=project_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        user_session=user_session,
        audit_service=audit_service,
    )
    employee_service = EmployeeService(
        session=session,
        employee_repo=employee_repo,
        resource_repo=resource_repo,
        user_session=user_session,
        audit_service=audit_service,
    )

    project_service = ProjectService(
        session,
        project_repo,
        task_repo,
        dependency_repo,
        assignment_repo,
        time_entry_repo,
        calendar_repo,
        cost_repo,
        user_session=user_session,
        audit_service=audit_service,
        module_catalog_service=module_runtime_service,
    )
    timesheet_service = TimesheetService(
        session=session,
        assignment_repo=assignment_repo,
        task_repo=task_repo,
        resource_repo=resource_repo,
        employee_repo=employee_repo,
        time_entry_repo=time_entry_repo,
        timesheet_period_repo=timesheet_period_repo,
        user_session=user_session,
        audit_service=audit_service,
        module_catalog_service=module_runtime_service,
    )
    time_service = timesheet_service
    project_resource_service = ProjectResourceService(
        project_resource_repo=project_resource_repo,
        resource_repo=resource_repo,
        session=session,
        user_session=user_session,
        audit_service=audit_service,
        module_catalog_service=module_runtime_service,
    )
    register_service = RegisterService(
        session=session,
        project_repo=project_repo,
        register_repo=register_repo,
        user_session=user_session,
        audit_service=audit_service,
        module_catalog_service=module_runtime_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        task_repo,
        dependency_repo,
        work_calendar_engine,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
    )
    task_service = TaskService(
        session,
        task_repo,
        dependency_repo,
        assignment_repo,
        time_entry_repo,
        timesheet_period_repo,
        timesheet_service,
        resource_repo,
        cost_repo,
        calendar_repo,
        work_calendar_engine,
        scheduling_engine,
        project_resource_repo,
        project_repo,
        user_session=user_session,
        audit_service=audit_service,
        approval_service=approval_service,
        module_catalog_service=module_runtime_service,
    )
    calendar_service = CalendarService(
        session,
        calendar_repo,
        task_repo,
        user_session=user_session,
        module_catalog_service=module_runtime_service,
    )
    resource_service = ResourceService(
        session,
        resource_repo,
        assignment_repo,
        project_resource_repo,
        time_entry_repo,
        employee_repo,
        user_session=user_session,
        audit_service=audit_service,
        module_catalog_service=module_runtime_service,
    )
    cost_service = CostService(
        session,
        cost_repo,
        project_repo,
        task_repo,
        user_session=user_session,
        audit_service=audit_service,
        approval_service=approval_service,
        module_catalog_service=module_runtime_service,
    )
    work_calendar_service = WorkCalendarService(
        session,
        work_calendar_repo,
        work_calendar_engine,
        user_session=user_session,
        module_catalog_service=module_runtime_service,
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
        user_session=user_session,
        module_catalog_service=module_runtime_service,
    )
    finance_service = FinanceService(
        project_repo=project_repo,
        task_repo=task_repo,
        resource_repo=resource_repo,
        cost_repo=cost_repo,
        project_resource_repo=project_resource_repo,
        reporting_service=reporting_service,
        user_session=user_session,
        module_catalog_service=module_runtime_service,
    )
    collaboration_service = CollaborationService(
        session=session,
        comment_repo=task_comment_repo,
        task_repo=task_repo,
        project_repo=project_repo,
        user_repo=user_repo,
        audit_repo=audit_repo,
        project_membership_repo=project_membership_repo,
        user_session=user_session,
        module_catalog_service=module_runtime_service,
    )
    portfolio_service = PortfolioService(
        session=session,
        intake_repo=portfolio_intake_repo,
        scenario_repo=portfolio_scenario_repo,
        project_repo=project_repo,
        resource_repo=resource_repo,
        reporting_service=reporting_service,
        user_session=user_session,
        module_catalog_service=module_runtime_service,
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
        module_catalog_service=module_runtime_service,
    )
    dashboard_service = DashboardService(
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        register_service=register_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        user_session=user_session,
        module_catalog_service=module_runtime_service,
    )
    data_import_service = DataImportService(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        cost_service=cost_service,
        module_catalog_service=module_runtime_service,
    )
    task_collaboration_store = TaskCollaborationStore(session_factory=lambda: session)
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
        platform_runtime_application_service=platform_runtime_application_service,
        module_runtime_service=module_runtime_service,
        module_catalog_service=module_catalog_service,
        time_service=time_service,
        auth_service=auth_service,
        organization_service=organization_service,
        employee_service=employee_service,
        access_service=access_service,
        audit_service=audit_service,
        approval_service=approval_service,
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


def build_service_dict(session: Session) -> dict[str, Any]:
    return build_service_graph(session).as_dict()
