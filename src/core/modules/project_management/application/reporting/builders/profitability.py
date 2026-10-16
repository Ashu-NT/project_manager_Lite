"""Reporting boundary: authorization and one resolved date, then canonical query."""

from __future__ import annotations

from datetime import UTC, date, datetime

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.revenue.commercial_projection_query import (
    CommercialProjectionQuery,
)
from src.core.modules.project_management.application.financials.revenue.dto.responses.commercial_response import (
    FinancialCommercialProjectionDto,
)
from src.core.modules.project_management.application.financials.revenue.mappers.commercial_response import (
    serialize_commercial_projection,
)
from src.core.modules.project_management.application.reporting.builders.access import (
    ReportingAccessPolicy,
)
from src.core.modules.project_management.application.reporting.builders.cost_policy import (
    ReportingCostPolicy,
)
from src.core.modules.project_management.contracts.reads.financials.invoicing.reader import (
    FinanceBillingReader,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError


class ProfitabilityReportBuilder(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        access: ReportingAccessPolicy,
        cost_policy: ReportingCostPolicy,
        project_repo: ProjectRepository,
        tenant_context_service: TenantContextService,
        billing_repo: ProjectBillingRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        billing_reader: FinanceBillingReader,
        module_catalog_service=None,
    ) -> None:
        self._access = access
        self._cost_policy = cost_policy
        self._project_repo = project_repo
        self._tenant_context_service = tenant_context_service
        self._billing_repo = billing_repo
        self._financial_profile_repo = financial_profile_repo
        self._billing_reader = billing_reader
        self._user_session = access.user_session
        self._module_catalog_service = module_catalog_service

    def get_project_commercial_projection(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
    ) -> FinancialCommercialProjectionDto:
        self._access.require_finance_view(
            "view project commercial projection", project_id=project_id
        )
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view commercial projection"
        )
        return serialize_commercial_projection(CommercialProjectionQuery(
            billing_repo=self._billing_repo,
            financial_profile_repo=self._financial_profile_repo,
            billing_reader=self._billing_reader,
            cost_totals=lambda project, cutoff: (
                self._cost_policy.compose_finance_policy(project, as_of=cutoff)[1].totals
            ),
        ).read(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            as_of_date=as_of_date or datetime.now(UTC).astimezone().date(),
            include_profitability=self._access.has_profitability_view(project_id),
        ))


__all__ = ["ProfitabilityReportBuilder"]
