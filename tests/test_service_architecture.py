from core.services._base_service import ServiceBase as LegacyServiceBase
from core.services.approval import ApprovalService
from core.services.approval_service import ApprovalService as LegacyApprovalService
from core.services.auth import AuthService
from core.services.auth_service import AuthService as LegacyAuthService
from core.services.audit import AuditService
from core.services.audit_service import AuditService as LegacyAuditService
from core.services.baseline import BaselineService
from core.services.baseline_service import BaselineService as LegacyBaselineService
from core.services.calendar import CalendarService
from core.services.cost import CostService
from core.services.dashboard import DashboardService
from core.services.project import ProjectResourceService, ProjectService
from core.services.project_calendar_service import CalendarService as LegacyCalendarService
from core.services.project_resource_service import ProjectResourceService as LegacyProjectResourceService
from core.services.project_service import ProjectService as LegacyProjectService
from core.services.reporting import ReportingService
from core.services.reporting_service import ReportingService as LegacyReportingService
from core.services.resource import ResourceService
from core.services.resource_service import ResourceService as LegacyResourceService
from core.services.scheduling import CPMTaskInfo, SchedulingEngine
from core.services.scheduling_service import CPMTaskInfo as LegacyCPMTaskInfo
from core.services.scheduling_service import SchedulingEngine as LegacySchedulingEngine
from core.services.task import TaskService
from core.services.task_service import TaskService as LegacyTaskService
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from core.services.work_calendar_engine import WorkCalendarEngine as LegacyWorkCalendarEngine
from core.services.work_calendar_service import WorkCalendarService as LegacyWorkCalendarService
from infra.services import ServiceGraph, build_service_graph


def test_service_graph_builder_wires_all_services(session):
    graph = build_service_graph(session)

    assert isinstance(graph, ServiceGraph)
    assert isinstance(graph.approval_service, ApprovalService)
    assert isinstance(graph.auth_service, AuthService)
    assert isinstance(graph.audit_service, AuditService)
    assert isinstance(graph.project_service, ProjectService)
    assert isinstance(graph.task_service, TaskService)
    assert isinstance(graph.resource_service, ResourceService)
    assert isinstance(graph.calendar_service, CalendarService)
    assert isinstance(graph.cost_service, CostService)
    assert isinstance(graph.work_calendar_engine, WorkCalendarEngine)
    assert isinstance(graph.work_calendar_service, WorkCalendarService)
    assert isinstance(graph.scheduling_engine, SchedulingEngine)
    assert isinstance(graph.reporting_service, ReportingService)
    assert isinstance(graph.baseline_service, BaselineService)
    assert isinstance(graph.dashboard_service, DashboardService)
    assert isinstance(graph.project_resource_service, ProjectResourceService)

    as_dict = graph.as_dict()
    assert as_dict["approval_service"] is graph.approval_service
    assert as_dict["auth_service"] is graph.auth_service
    assert as_dict["audit_service"] is graph.audit_service
    assert as_dict["dashboard_service"] is graph.dashboard_service
    assert as_dict["project_resource_service"] is graph.project_resource_service
    assert as_dict["session"] is session


def test_legacy_service_imports_point_to_new_packages():
    assert LegacyServiceBase.__name__ == "ServiceBase"
    assert LegacyApprovalService is ApprovalService
    assert LegacyAuthService is AuthService
    assert LegacyAuditService is AuditService
    assert LegacyProjectService is ProjectService
    assert LegacyProjectResourceService is ProjectResourceService
    assert LegacyTaskService is TaskService
    assert LegacyResourceService is ResourceService
    assert LegacyCalendarService is CalendarService
    assert LegacySchedulingEngine is SchedulingEngine
    assert LegacyCPMTaskInfo is CPMTaskInfo
    assert LegacyWorkCalendarEngine is WorkCalendarEngine
    assert LegacyWorkCalendarService is WorkCalendarService
    assert LegacyReportingService is ReportingService
    assert LegacyBaselineService is BaselineService
