from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.budgets.queries import (
    BudgetsWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.configuration.queries import (
    ConfigurationWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.cost.queries import (
    CostWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.financial_changes.queries import (
    FinancialChangesWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.forecasts.queries import (
    ForecastsWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.integration.queries import (
    IntegrationWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.invoicing.queries import (
    InvoicingWorkspaceQueries,
)
from src.core.modules.project_management.application.financials.rate_cards.queries import (
    RateCardsWorkspaceQueries,
)
from src.core.modules.project_management.contracts.reads.financials.finance_billing_reader import (
    FinanceBillingReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_budget_reader import (
    FinanceBudgetReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_change_reader import (
    FinanceChangeReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_forecast_reader import (
    FinanceForecastReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_integration_reader import (
    FinanceIntegrationReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_lookup_reader import (
    FinanceLookupReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_planned_cost_reader import (
    FinancePlannedCostReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_rate_reader import (
    FinanceRateReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_setup_reader import (
    FinanceSetupReader,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)


class ProjectFinanceWorkspaceQuery(
    ConfigurationWorkspaceQueries,
    CostWorkspaceQueries,
    BudgetsWorkspaceQueries,
    FinancialChangesWorkspaceQueries,
    ForecastsWorkspaceQueries,
    RateCardsWorkspaceQueries,
    InvoicingWorkspaceQueries,
    IntegrationWorkspaceQueries,
    ProjectManagementModuleGuardMixin,
):
    """Canonical project-level read projection for the Finance workspace."""

    def __init__(
        self,
        *,
        setup_reader: FinanceSetupReader,
        lookup_reader: FinanceLookupReader | None = None,
        budget_reader: FinanceBudgetReader | None = None,
        planned_cost_reader: FinancePlannedCostReader | None = None,
        forecast_reader: FinanceForecastReader | None = None,
        rate_reader: FinanceRateReader | None = None,
        change_reader: FinanceChangeReader | None = None,
        billing_reader: FinanceBillingReader | None = None,
        integration_reader: FinanceIntegrationReader | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        module_catalog_service=None,
        accounting_capability=None,
    ) -> None:
        self._setup_reader = setup_reader
        self._lookup_reader = lookup_reader
        self._budget_reader = budget_reader
        self._planned_cost_reader = planned_cost_reader
        self._forecast_reader = forecast_reader
        self._rate_reader = rate_reader
        self._change_reader = change_reader
        self._billing_reader = billing_reader
        self._integration_reader = integration_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._accounting_capability = accounting_capability

    def active_scope_ids(self) -> tuple[str, str]:
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="resolve Project Finance scope"
        )
        return scope.tenant_id, scope.organization_id

    def search_finance_projects(
        self, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        return self._search_projects(
            permission="finance.read",
            operation="search Project Finance projects",
            require_active_profile=False,
            request=request,
        )

    def resolve_finance_project(self, project_id: str) -> FinanceLookupOptionFact | None:
        return self._resolve_project(
            project_id,
            permission="finance.read",
            operation="resolve Project Finance project",
            require_active_profile=False,
        )

    def _search_projects(
        self,
        *,
        permission: str,
        operation: str,
        require_active_profile: bool,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts:
        require_permission(self._user_session, permission, operation_label=operation)
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
        )
        return self._require_lookup_reader().search_projects(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=self._allowed_project_ids(permission),
            require_active_finance_profile=require_active_profile,
            request=request,
        )

    def _resolve_project(
        self,
        project_id: str,
        *,
        permission: str,
        operation: str,
        require_active_profile: bool,
    ) -> FinanceLookupOptionFact | None:
        normalized_id = str(project_id or "").strip()
        if not normalized_id:
            return None
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session,
            normalized_id,
            permission,
            operation_label=operation,
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
        )
        return self._require_lookup_reader().get_project_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=normalized_id,
            allowed_project_ids=self._allowed_project_ids(permission),
            require_active_finance_profile=require_active_profile,
        )

    def _allowed_project_ids(self, permission: str) -> tuple[str, ...] | None:
        if self._user_session is None or not self._user_session.is_project_restricted():
            return None
        return tuple(sorted(self._user_session.project_ids_for(permission)))

    def _require_lookup_reader(self) -> FinanceLookupReader:
        if self._lookup_reader is None:
            raise RuntimeError("Finance Lookup Reader is not configured.")
        return self._lookup_reader

    def _has_project_permission(self, project_id: str, permission: str) -> bool:
        session = self._user_session
        return bool(
            session is not None
            and session.has_permission(permission)
            and session.has_project_permission(project_id, permission)
        )

__all__ = ["ProjectFinanceWorkspaceQuery"]
