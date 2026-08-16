from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.scheduling.baseline import BaselineRepository
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.contracts.reads.financials.evm_series_reader import (
    EvmSeriesReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_snapshot_reader import (
    FinanceSnapshotReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.modules.project_management.application.scheduling.services.scheduling_engine import SchedulingEngine
from src.core.platform.common.service_base import ServiceBase
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin

from src.core.modules.project_management.infrastructure.reporting.builders.baseline_compare import ReportingBaselineCompareMixin
from src.core.modules.project_management.infrastructure.reporting.builders.cost_breakdown import ReportingCostBreakdownMixin
from src.core.modules.project_management.infrastructure.reporting.builders.evm import ReportingEvmMixin
from src.core.modules.project_management.infrastructure.reporting.builders.kpi import ReportingKpiMixin
from src.core.modules.project_management.infrastructure.reporting.builders.labor import ReportingLaborMixin
from src.core.modules.project_management.infrastructure.reporting.builders.profitability import ReportingProfitabilityMixin
from src.core.modules.project_management.infrastructure.reporting.builders.variance import ReportingVarianceMixin


class ReportingService(
    ProjectManagementModuleGuardMixin,
    ReportingCostBreakdownMixin,
    ReportingBaselineCompareMixin,
    ReportingProfitabilityMixin,
    ReportingVarianceMixin,
    ReportingEvmMixin,
    ReportingLaborMixin,
    ReportingKpiMixin,
    ServiceBase,
):
    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        scheduling_engine: SchedulingEngine,
        calendar: CalendarProtocol,
        baseline_repo: BaselineRepository,
        project_resource_repo: ProjectResourceRepository,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
        evm_series_reader: EvmSeriesReader,
        finance_snapshot_reader: FinanceSnapshotReader,
        financial_profile_repo,
        billing_repo: ProjectBillingRepository,
        user_session=None,
        module_catalog_service=None,
    ):
        super().__init__(session)
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._scheduling_engine: SchedulingEngine = scheduling_engine
        self._calendar: CalendarProtocol = calendar
        self._baseline_repo: BaselineRepository = baseline_repo
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        self._rate_resolver: LaborRateResolver = rate_resolver
        self._tenant_context_service: TenantContextService = tenant_context_service
        self._evm_series_reader: EvmSeriesReader = evm_series_reader
        self._finance_snapshot_reader: FinanceSnapshotReader = finance_snapshot_reader
        self._financial_profile_repo = financial_profile_repo
        self._billing_repo: ProjectBillingRepository = billing_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _require_view(self, operation_label: str, *, project_id: str | None = None) -> None:
        require_permission(self._user_session, "report.view", operation_label=operation_label)
        if project_id is not None:
            require_project_permission(
                self._user_session,
                project_id,
                "report.view",
                operation_label=operation_label,
            )

    def _require_finance_view(self, operation_label: str, *, project_id: str) -> None:
        """Gate for report methods whose entire result is Project Finance
        authority data (EVM, cost breakdown, cost source breakdown, labor
        cost). """
        require_permission(self._user_session, "finance.read", operation_label=operation_label)
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label=operation_label,
        )

    def _require_finance_sensitive_view(self, operation_label: str, *, project_id: str) -> None:
        """Gate for report methods that expose individually-identified
        resource labor rates/costs — the same sensitivity tier
        ``FinanceService`` protects with ``finance.read_sensitive``."""
        require_permission(
            self._user_session, "finance.read_sensitive", operation_label=operation_label
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read_sensitive",
            operation_label=operation_label,
        )

    def _has_finance_view(self, project_id: str) -> bool:
        """Non-raising finance.read check for reports that mix financial and
        non-financial content and must redact rather than deny outright."""
        return bool(
            self._user_session is not None
            and self._user_session.has_project_permission(project_id, "finance.read")
        )

    def _has_profitability_view(self, project_id: str) -> bool:
        """Non-raising finance.read_profitability check (ADR-PF-010) for the
        commercial projection, which mixes ordinary billing-progress figures
        with commercial margin and must redact only the margin family rather
        than deny the whole call."""
        return bool(
            self._user_session is not None
            and self._user_session.has_project_permission(
                project_id, "finance.read_profitability"
            )
        )
