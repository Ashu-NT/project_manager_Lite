from core.platform.common.service_base import ServiceBase as LegacyServiceBase
from core.platform.access import AccessControlService
from core.platform.approval import ApprovalService
from core.platform.approval.service import ApprovalService as LegacyApprovalService
from core.platform.auth import AuthService
from core.platform.auth.service import AuthService as LegacyAuthService
from core.platform.audit import AuditService
from core.platform.audit.service import AuditService as LegacyAuditService
from core.platform.org import EmployeeService
from core.modules.project_management.services.baseline import BaselineService
from core.modules.project_management.services.baseline.service import BaselineService as LegacyBaselineService
from core.modules.project_management.services.calendar import CalendarService
from core.modules.project_management.services.collaboration import CollaborationService
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.dashboard import DashboardService
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.finance.service import FinanceService as LegacyFinanceService
from core.modules.project_management.services.portfolio import PortfolioService
from core.modules.project_management.services.project import ProjectResourceService, ProjectService
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.register.service import RegisterService as LegacyRegisterService
from core.modules.project_management.services.calendar.service import CalendarService as LegacyCalendarService
from core.modules.project_management.services.project.resource_service import ProjectResourceService as LegacyProjectResourceService
from core.modules.project_management.services.project.service import ProjectService as LegacyProjectService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.reporting.service import ReportingService as LegacyReportingService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.resource.service import ResourceService as LegacyResourceService
from core.modules.project_management.services.scheduling import CPMTaskInfo, SchedulingEngine
from core.modules.project_management.services.scheduling.engine import CPMTaskInfo as LegacyCPMTaskInfo
from core.modules.project_management.services.scheduling.engine import SchedulingEngine as LegacySchedulingEngine
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.task.service import TaskService as LegacyTaskService
from core.modules.project_management.services.timesheet import TimesheetService
from core.modules.project_management.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from core.modules.project_management.services.work_calendar.engine import WorkCalendarEngine as LegacyWorkCalendarEngine
from core.modules.project_management.services.work_calendar.service import WorkCalendarService as LegacyWorkCalendarService
from infra.platform.services import ServiceGraph, build_service_graph


def test_service_graph_builder_wires_all_services(session):
    graph = build_service_graph(session)

    assert isinstance(graph, ServiceGraph)
    assert isinstance(graph.approval_service, ApprovalService)
    assert isinstance(graph.auth_service, AuthService)
    assert isinstance(graph.employee_service, EmployeeService)
    assert isinstance(graph.access_service, AccessControlService)
    assert isinstance(graph.audit_service, AuditService)
    assert isinstance(graph.collaboration_service, CollaborationService)
    assert isinstance(graph.project_service, ProjectService)
    assert isinstance(graph.task_service, TaskService)
    assert isinstance(graph.timesheet_service, TimesheetService)
    assert isinstance(graph.resource_service, ResourceService)
    assert isinstance(graph.calendar_service, CalendarService)
    assert isinstance(graph.cost_service, CostService)
    assert isinstance(graph.finance_service, FinanceService)
    assert isinstance(graph.work_calendar_engine, WorkCalendarEngine)
    assert isinstance(graph.work_calendar_service, WorkCalendarService)
    assert isinstance(graph.scheduling_engine, SchedulingEngine)
    assert isinstance(graph.reporting_service, ReportingService)
    assert isinstance(graph.baseline_service, BaselineService)
    assert isinstance(graph.dashboard_service, DashboardService)
    assert isinstance(graph.portfolio_service, PortfolioService)
    assert isinstance(graph.register_service, RegisterService)
    assert isinstance(graph.project_resource_service, ProjectResourceService)

    as_dict = graph.as_dict()
    assert as_dict["approval_service"] is graph.approval_service
    assert as_dict["auth_service"] is graph.auth_service
    assert as_dict["employee_service"] is graph.employee_service
    assert as_dict["access_service"] is graph.access_service
    assert as_dict["audit_service"] is graph.audit_service
    assert as_dict["collaboration_service"] is graph.collaboration_service
    assert as_dict["dashboard_service"] is graph.dashboard_service
    assert as_dict["finance_service"] is graph.finance_service
    assert as_dict["portfolio_service"] is graph.portfolio_service
    assert as_dict["register_service"] is graph.register_service
    assert as_dict["project_resource_service"] is graph.project_resource_service
    assert as_dict["timesheet_service"] is graph.timesheet_service
    assert as_dict["session"] is session


def test_legacy_service_imports_point_to_new_packages():
    assert LegacyServiceBase.__name__ == "ServiceBase"
    assert LegacyApprovalService is ApprovalService
    assert LegacyAuthService is AuthService
    assert LegacyAuditService is AuditService
    assert LegacyProjectService is ProjectService
    assert LegacyProjectResourceService is ProjectResourceService
    assert LegacyRegisterService is RegisterService
    assert LegacyTaskService is TaskService
    assert LegacyResourceService is ResourceService
    assert LegacyCalendarService is CalendarService
    assert LegacySchedulingEngine is SchedulingEngine
    assert LegacyCPMTaskInfo is CPMTaskInfo
    assert LegacyWorkCalendarEngine is WorkCalendarEngine
    assert LegacyWorkCalendarService is WorkCalendarService
    assert LegacyReportingService is ReportingService
    assert LegacyBaselineService is BaselineService
    assert LegacyFinanceService is FinanceService
