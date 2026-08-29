from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.reads.financials.finance_setup_reader import (
    FinanceSetupReader,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_setup_facts import (
    FinanceSetupFacts,
)
from src.core.modules.project_management.contracts.reads.financials.finance_budget_reader import (
    FinanceBudgetReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_planned_cost_reader import (
    FinancePlannedCostReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_forecast_reader import (
    FinanceForecastReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_rate_reader import (
    FinanceRateReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_change_reader import (
    FinanceChangeReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_billing_reader import (
    FinanceBillingReader,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinanceBudgetWorkspaceFacts,
    FinancePageFacts,
    FinancePageRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_planned_cost_facts import (
    FinancePlannedCostWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_forecast_facts import (
    FinanceForecastWorkspaceFacts,
    ForecastLineRequest,
    ForecastVersionRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    FinanceRateWorkspaceFacts,
    RateCardRequest,
    RateLineRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_change_facts import (
    FinanceChangeWorkspaceFacts,
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingScheduleQuery,
    FinanceBillingWorkspaceFacts,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class ProjectFinanceWorkspaceQuery(ProjectManagementModuleGuardMixin):
    """Canonical project-level read projection for the Finance workspace."""

    def __init__(
        self,
        *,
        setup_reader: FinanceSetupReader,
        budget_reader: FinanceBudgetReader | None = None,
        planned_cost_reader: FinancePlannedCostReader | None = None,
        forecast_reader: FinanceForecastReader | None = None,
        rate_reader: FinanceRateReader | None = None,
        change_reader: FinanceChangeReader | None = None,
        billing_reader: FinanceBillingReader | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._setup_reader = setup_reader
        self._budget_reader = budget_reader
        self._planned_cost_reader = planned_cost_reader
        self._forecast_reader = forecast_reader
        self._rate_reader = rate_reader
        self._change_reader = change_reader
        self._billing_reader = billing_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_budget_workspace(
        self,
        project_id: str,
        *,
        selected_budget_id: str = "",
        version_request: FinancePageRequest | None = None,
        line_request: FinancePageRequest | None = None,
    ) -> FinanceBudgetWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project budgets",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project budgets",
        )
        if self._budget_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Budget Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project budgets"
        )
        normalized_budget_id = str(selected_budget_id or "").strip()
        versions = self._budget_reader.list_versions(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=version_request or FinancePageRequest(sort_key="revision"),
        )
        requested_lines = line_request or FinancePageRequest(sort_key="metaText")
        lines = (
            self._budget_reader.list_lines(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                budget_id=normalized_budget_id,
                request=requested_lines,
            )
            if normalized_budget_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_lines.normalized_page,
                page_size=requested_lines.normalized_page_size,
                sort_key=(requested_lines.sort_key or "metaText"),
                sort_direction=(
                    "asc" if requested_lines.sort_direction == "asc" else "desc"
                ),
            )
        )
        return FinanceBudgetWorkspaceFacts(
            selected_budget_id=normalized_budget_id,
            versions=versions,
            lines=lines,
        )

    def get_planned_cost_workspace(
        self,
        project_id: str,
        *,
        selected_version_id: str = "",
        version_request: FinancePageRequest | None = None,
        line_request: FinancePageRequest | None = None,
    ) -> FinancePlannedCostWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project planned costs",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project planned costs",
        )
        if self._planned_cost_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Planned Cost Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project planned costs"
        )
        normalized_version_id = str(selected_version_id or "").strip()
        versions = self._planned_cost_reader.list_versions(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=version_request or FinancePageRequest(sort_key="revision"),
        )
        requested_lines = line_request or FinancePageRequest(sort_key="title")
        lines = (
            self._planned_cost_reader.list_lines(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                version_id=normalized_version_id,
                request=requested_lines,
            )
            if normalized_version_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_lines.normalized_page,
                page_size=requested_lines.normalized_page_size,
                sort_key=(requested_lines.sort_key or "title"),
                sort_direction=(
                    "asc" if requested_lines.sort_direction == "asc" else "desc"
                ),
            )
        )
        return FinancePlannedCostWorkspaceFacts(
            selected_version_id=normalized_version_id,
            versions=versions,
            lines=lines,
        )

    def get_forecast_workspace(
        self,
        project_id: str,
        *,
        selected_forecast_id: str = "",
        version_request: ForecastVersionRequest | None = None,
        line_request: ForecastLineRequest | None = None,
    ) -> FinanceForecastWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project forecasts",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project forecasts",
        )
        if self._forecast_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Forecast Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project forecasts"
        )
        versions = self._forecast_reader.list_versions(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=version_request or ForecastVersionRequest(),
        )
        requested_id = str(selected_forecast_id or "").strip()
        selected = (
            self._forecast_reader.get_version(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                forecast_id=requested_id,
            )
            if requested_id
            else None
        )
        resolved_id = selected.id if selected is not None else ""
        requested_lines = line_request or ForecastLineRequest()
        lines = (
            self._forecast_reader.list_lines(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                forecast_id=resolved_id,
                request=requested_lines,
            )
            if resolved_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_lines.normalized_page,
                page_size=requested_lines.normalized_page_size,
                sort_key=requested_lines.normalized_sort_key,
                sort_direction=(
                    "asc" if requested_lines.sort_direction == "asc" else "desc"
                ),
            )
        )
        return FinanceForecastWorkspaceFacts(
            selected_forecast_id=resolved_id,
            selected_forecast=selected,
            versions=versions,
            lines=lines,
        )

    def get_rate_workspace(
        self,
        project_id: str,
        *,
        selected_rate_card_id: str = "",
        card_request: RateCardRequest | None = None,
        line_request: RateLineRequest | None = None,
    ) -> FinanceRateWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project rates",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project rates",
        )
        # Rates expose identified labor pricing; the established Finance policy
        # denies this detail rather than returning a partial monetary projection.
        require_permission(
            self._user_session,
            "finance.read_sensitive",
            operation_label="view sensitive project rates",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read_sensitive",
            operation_label="view sensitive project rates",
        )
        if self._rate_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Rate Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project rates"
        )
        cards = self._rate_reader.list_cards(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=card_request or RateCardRequest(),
        )
        requested_id = str(selected_rate_card_id or "").strip()
        selected = (
            self._rate_reader.get_card(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                rate_card_id=requested_id,
            )
            if requested_id
            else None
        )
        resolved_id = selected.id if selected is not None else ""
        requested_lines = line_request or RateLineRequest()
        lines = (
            self._rate_reader.list_lines(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                rate_card_id=resolved_id,
                request=requested_lines,
            )
            if resolved_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_lines.normalized_page,
                page_size=requested_lines.normalized_page_size,
                sort_key=requested_lines.normalized_sort_key,
                sort_direction=(
                    "asc" if requested_lines.sort_direction == "asc" else "desc"
                ),
            )
        )
        return FinanceRateWorkspaceFacts(
            selected_rate_card_id=resolved_id,
            selected_rate_card=selected,
            cards=cards,
            lines=lines,
        )

    def get_change_workspace(
        self,
        project_id: str,
        *,
        selected_change_id: str = "",
        change_request: FinancialChangeRequestQuery | None = None,
        impact_request: FinancialChangeImpactQuery | None = None,
    ) -> FinanceChangeWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project financial changes",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project financial changes",
        )
        if self._change_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Change Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project financial changes"
        )
        changes = self._change_reader.list_changes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=change_request or FinancialChangeRequestQuery(),
        )
        requested_id = str(selected_change_id or "").strip()
        selected = (
            self._change_reader.get_change(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                change_id=requested_id,
            )
            if requested_id
            else None
        )
        resolved_id = selected.id if selected is not None else ""
        requested_impacts = impact_request or FinancialChangeImpactQuery()
        impacts = (
            self._change_reader.list_impacts(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                change_id=resolved_id,
                request=requested_impacts,
            )
            if resolved_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_impacts.normalized_page,
                page_size=requested_impacts.normalized_page_size,
                sort_key=requested_impacts.normalized_sort_key,
                sort_direction=(
                    "asc" if requested_impacts.sort_direction == "asc" else "desc"
                ),
            )
        )
        return FinanceChangeWorkspaceFacts(
            selected_change_id=resolved_id,
            selected_change=selected,
            changes=changes,
            impacts=impacts,
        )

    def get_billing_read_workspace(
        self,
        project_id: str,
        *,
        selected_preparation_id: str = "",
        schedule_request: BillingScheduleQuery | None = None,
        preparation_request: BillingPreparationQuery | None = None,
        line_request: BillingPreparationLineQuery | None = None,
    ) -> FinanceBillingWorkspaceFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project commercial billing evidence",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project commercial billing evidence",
        )
        if self._billing_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Billing Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project commercial billing evidence"
        )
        arguments = {
            "tenant_id": scope.tenant_id,
            "organization_id": scope.organization_id,
            "project_id": project_id,
        }
        profile = self._billing_reader.get_profile(**arguments)
        schedule = self._billing_reader.list_schedule(
            **arguments,
            request=schedule_request or BillingScheduleQuery(),
        )
        preparations = self._billing_reader.list_preparations(
            **arguments,
            request=preparation_request or BillingPreparationQuery(),
        )
        requested_id = str(selected_preparation_id or "").strip()
        selected = (
            self._billing_reader.get_preparation(
                **arguments,
                preparation_id=requested_id,
            )
            if requested_id
            else None
        )
        resolved_id = selected.id if selected is not None else ""
        requested_lines = line_request or BillingPreparationLineQuery()
        lines = (
            self._billing_reader.list_preparation_lines(
                **arguments,
                preparation_id=resolved_id,
                request=requested_lines,
            )
            if resolved_id
            else FinancePageFacts(
                items=(),
                total=0,
                page=requested_lines.normalized_page,
                page_size=requested_lines.normalized_page_size,
                sort_key=requested_lines.normalized_sort_key,
                sort_direction=(
                    "asc" if requested_lines.sort_direction == "asc" else "desc"
                ),
            )
        )
        return FinanceBillingWorkspaceFacts(
            profile=profile,
            selected_preparation_id=resolved_id,
            selected_preparation=selected,
            schedule=schedule,
            preparations=preparations,
            lines=lines,
        )

    def get_setup_workspace(self, project_id: str) -> FinanceSetupFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project finance setup",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project finance setup",
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance Setup Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project finance setup"
        )
        setup = self._setup_reader.get_setup(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
        )
        if setup is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        return setup

__all__ = [
    "ProjectFinanceWorkspaceQuery",
]
