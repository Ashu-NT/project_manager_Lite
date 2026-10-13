"""Labor mixin — thin reporting delegate.

Business logic lives in financials/costs/labor_cost.py.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.financials.cost.engines.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    LaborDetailsResult,
    LaborResourceRow,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError


class ReportingLaborMixin:
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _project_resource_repo: ProjectResourceRepository
    _rate_resolver: LaborRateResolver
    _tenant_context_service: TenantContextService
    _financial_profile_repo: ProjectFinancialProfileRepository

    def _make_labor_engine(self) -> LaborCostEngine:
        return LaborCostEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        )

    def calculate_project_labor_details(
        self, project_id: str, as_of: date | None = None
    ) -> LaborDetailsResult:
        # Resource-identified rate/cost rows require the finance.read_sensitive tier,
        # matching FinanceService's own redaction policy.
        self._require_finance_sensitive_view("view labor details", project_id=project_id)
        resolved_as_of = as_of or date.today()
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
