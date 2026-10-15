"""Labor report builder -- thin reporting delegate.

Business logic lives in financials/cost/engines/labor_cost.py.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.dto import (
    LaborDetailsResult,
    LaborResourceRow,
)
from src.core.modules.project_management.application.financials.cost.engines.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.application.reporting.builders.access import (
    ReportingAccessPolicy,
)
from src.core.modules.project_management.contracts.reads.financials.finance_snapshot_reader import (
    FinanceSnapshotReader,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError


class LaborReportBuilder(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        access: ReportingAccessPolicy,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
        finance_snapshot_reader: FinanceSnapshotReader,
        module_catalog_service=None,
    ) -> None:
        self._access = access
        self._rate_resolver = rate_resolver
        self._tenant_context_service = tenant_context_service
        self._finance_snapshot_reader = finance_snapshot_reader
        self._user_session = access.user_session
        self._module_catalog_service = module_catalog_service

    def _make_labor_engine(self) -> LaborCostEngine:
        return LaborCostEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        )

    def calculate_project_labor_details(
        self, project_id: str, as_of: date | None = None
    ) -> LaborDetailsResult:
        # Resource-identified rate/cost rows require the finance.read_sensitive tier,
        # matching FinanceSnapshotQueryHandler's own redaction policy.
        self._access.require_finance_sensitive_view("view labor details", project_id=project_id)
        resolved_as_of = as_of or date.today()  # noqa: DTZ011
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="read labor reporting facts"
        )
        facts = self._finance_snapshot_reader.read_facts(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id,
            project_id=project_id, as_of=resolved_as_of,
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return self._make_labor_engine().calculate_project_labor_details(
            project_id, resolved_as_of, facts=facts,
        )

    def get_project_labor_details(
        self, project_id: str, as_of: date | None = None
    ) -> list[LaborResourceRow]:
        return list(self.calculate_project_labor_details(project_id, as_of).rows)


__all__ = ["LaborReportBuilder"]
