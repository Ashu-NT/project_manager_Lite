from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from application.platform import PlatformRuntimeApplicationService
from core.platform.access import AccessControlService
from core.platform.approval import ApprovalService
from core.platform.audit import AuditService
from core.platform.auth import AuthService
from core.platform.auth.session import UserSessionContext
from core.platform.documents import DocumentService
from core.platform.modules.runtime import ModuleCatalogService, ModuleRuntimeService
from core.platform.org import DepartmentService, EmployeeService, OrganizationService, SiteService
from core.platform.party import PartyService
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
from infra.platform.service_registration import (
    build_platform_service_bundle,
    build_project_management_service_bundle,
    build_repository_bundle,
)


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
    document_service: DocumentService
    party_service: PartyService
    department_service: DepartmentService
    site_service: SiteService
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
            "document_service": self.document_service,
            "party_service": self.party_service,
            "department_service": self.department_service,
            "site_service": self.site_service,
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
    repositories = build_repository_bundle(session)
    platform_services = build_platform_service_bundle(session, repositories)
    project_management_services = build_project_management_service_bundle(
        session,
        repositories,
        platform_services,
    )
    return ServiceGraph(
        session=session,
        user_session=platform_services.user_session,
        platform_runtime_application_service=platform_services.platform_runtime_application_service,
        module_runtime_service=platform_services.module_runtime_service,
        module_catalog_service=platform_services.module_catalog_service,
        time_service=project_management_services.time_service,
        auth_service=platform_services.auth_service,
        organization_service=platform_services.organization_service,
        document_service=platform_services.document_service,
        party_service=platform_services.party_service,
        department_service=platform_services.department_service,
        site_service=platform_services.site_service,
        employee_service=platform_services.employee_service,
        access_service=platform_services.access_service,
        audit_service=platform_services.audit_service,
        approval_service=platform_services.approval_service,
        collaboration_service=project_management_services.collaboration_service,
        project_service=project_management_services.project_service,
        task_service=project_management_services.task_service,
        timesheet_service=project_management_services.timesheet_service,
        calendar_service=project_management_services.calendar_service,
        resource_service=project_management_services.resource_service,
        cost_service=project_management_services.cost_service,
        finance_service=project_management_services.finance_service,
        work_calendar_engine=project_management_services.work_calendar_engine,
        work_calendar_service=project_management_services.work_calendar_service,
        scheduling_engine=project_management_services.scheduling_engine,
        reporting_service=project_management_services.reporting_service,
        baseline_service=project_management_services.baseline_service,
        dashboard_service=project_management_services.dashboard_service,
        portfolio_service=project_management_services.portfolio_service,
        register_service=project_management_services.register_service,
        project_resource_service=project_management_services.project_resource_service,
        data_import_service=project_management_services.data_import_service,
        task_collaboration_store=project_management_services.task_collaboration_store,
    )


def build_service_dict(session: Session) -> dict[str, Any]:
    return build_service_graph(session).as_dict()
