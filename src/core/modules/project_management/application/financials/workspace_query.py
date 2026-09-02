from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.reads.financials.finance_setup_reader import (
    FinanceSetupReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_lookup_reader import (
    FinanceLookupReader,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_setup_facts import (
    FinanceSetupFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
    ManualActualDefaultsFacts,
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
    AccountingStatusFact,
    AccountingStatusQuery,
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
        lookup_reader: FinanceLookupReader | None = None,
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
        self._lookup_reader = lookup_reader
        self._budget_reader = budget_reader
        self._planned_cost_reader = planned_cost_reader
        self._forecast_reader = forecast_reader
        self._rate_reader = rate_reader
        self._change_reader = change_reader
        self._billing_reader = billing_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

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

    def search_manual_actual_projects(
        self, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        return self._search_projects(
            permission="project_cost.create",
            operation="search projects eligible for manual actuals",
            require_active_profile=True,
            request=request,
        )

    def resolve_manual_actual_project(
        self, project_id: str
    ) -> FinanceLookupOptionFact | None:
        return self._resolve_project(
            project_id,
            permission="project_cost.create",
            operation="resolve project eligible for manual actuals",
            require_active_profile=True,
        )

    def search_manual_actual_tasks(
        self,
        project_id: str,
        *,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts:
        scope = self._require_manual_actual_lookup(project_id, "search manual actual tasks")
        return self._require_lookup_reader().search_tasks(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def resolve_manual_actual_task(
        self, project_id: str, task_id: str
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_manual_actual_lookup(project_id, "resolve manual actual task")
        return self._require_lookup_reader().get_task_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            task_id=str(task_id or "").strip(),
        )

    def search_manual_actual_cost_codes(
        self,
        project_id: str,
        *,
        request: ManualActualCostCodeQuery,
    ) -> FinanceLookupPageFacts:
        scope = self._require_manual_actual_lookup(
            project_id, "search manual actual cost codes"
        )
        return self._require_lookup_reader().search_cost_codes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def resolve_manual_actual_cost_code(
        self,
        project_id: str,
        cost_code_id: str,
        *,
        effective_on=None,
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_manual_actual_lookup(
            project_id, "resolve manual actual cost code"
        )
        return self._require_lookup_reader().get_cost_code_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            cost_code_id=str(cost_code_id or "").strip(),
            effective_on=effective_on,
        )

    def get_manual_actual_defaults(self, project_id: str) -> ManualActualDefaultsFacts:
        scope = self._require_manual_actual_lookup(
            project_id, "load manual actual defaults"
        )
        defaults = self._require_lookup_reader().get_manual_actual_defaults(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
        )
        if defaults is None:
            raise NotFoundError(
                "An active project financial profile is required.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_ACTIVE",
            )
        return defaults

    def search_budget_tasks(
        self, project_id: str, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_budget_lookup(project_id, "search Budget tasks")
        return self._require_lookup_reader().search_tasks(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def resolve_budget_task(
        self, project_id: str, task_id: str
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_budget_lookup(project_id, "resolve Budget task")
        return self._require_lookup_reader().get_task_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            task_id=str(task_id or "").strip(),
        )

    def search_budget_cost_codes(
        self, project_id: str, *, request: ManualActualCostCodeQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_budget_lookup(project_id, "search Budget cost codes")
        return self._require_lookup_reader().search_cost_codes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def resolve_budget_cost_code(
        self, project_id: str, cost_code_id: str, *, effective_on=None
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_budget_lookup(project_id, "resolve Budget cost code")
        return self._require_lookup_reader().get_cost_code_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            cost_code_id=str(cost_code_id or "").strip(),
            effective_on=effective_on,
        )

    def search_financial_change_target_lines(
        self,
        project_id: str,
        change_id: str,
        impact_type: str,
        *,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts:
        scope = self._require_financial_change_lookup(
            project_id, "search Financial Change target lines"
        )
        return self._require_lookup_reader().search_change_target_lines(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            change_id=str(change_id or "").strip(),
            impact_type=str(impact_type or "").strip().lower(),
            request=request,
        )

    def resolve_financial_change_target_line(
        self,
        project_id: str,
        change_id: str,
        impact_type: str,
        line_id: str,
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_financial_change_lookup(
            project_id, "resolve Financial Change target line"
        )
        return self._require_lookup_reader().get_change_target_line_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            change_id=str(change_id or "").strip(),
            impact_type=str(impact_type or "").strip().lower(),
            line_id=str(line_id or "").strip(),
        )

    def _require_financial_change_lookup(self, project_id: str, operation: str):
        normalized_id = str(project_id or "").strip()
        require_permission(
            self._user_session, "financial_change.manage", operation_label=operation
        )
        require_project_permission(
            self._user_session,
            normalized_id,
            "financial_change.manage",
            operation_label=operation,
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
        )

    def search_forecast_risks(
        self, project_id: str, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_forecast_lookup(project_id, "search Forecast risks")
        return self._require_lookup_reader().search_eligible_risks(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def search_forecast_tasks(
        self, project_id: str, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_forecast_lookup(project_id, "search Forecast tasks")
        return self._require_lookup_reader().search_tasks(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def search_forecast_cost_codes(
        self,
        project_id: str,
        *,
        request: ManualActualCostCodeQuery,
    ) -> FinanceLookupPageFacts:
        scope = self._require_forecast_lookup(project_id, "search Forecast cost codes")
        return self._require_lookup_reader().search_cost_codes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )

    def resolve_forecast_risk(
        self, project_id: str, risk_id: str
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_forecast_lookup(project_id, "resolve Forecast risk")
        return self._require_lookup_reader().get_eligible_risk_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            risk_id=str(risk_id or "").strip(),
        )

    def _require_forecast_lookup(self, project_id: str, operation: str):
        normalized_id = str(project_id or "").strip()
        require_permission(self._user_session, "forecast.manage", operation_label=operation)
        require_project_permission(
            self._user_session,
            normalized_id,
            "forecast.manage",
            operation_label=operation,
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
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

    def _require_manual_actual_lookup(self, project_id: str, operation: str):
        normalized_id = str(project_id or "").strip()
        require_permission(
            self._user_session, "project_cost.create", operation_label=operation
        )
        require_project_permission(
            self._user_session,
            normalized_id,
            "project_cost.create",
            operation_label=operation,
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
        )

    def _require_budget_lookup(self, project_id: str, operation: str):
        normalized_id = str(project_id or "").strip()
        require_permission(self._user_session, "budget.manage", operation_label=operation)
        require_project_permission(
            self._user_session,
            normalized_id,
            "budget.manage",
            operation_label=operation,
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
        )

    def _allowed_project_ids(self, permission: str) -> tuple[str, ...] | None:
        if self._user_session is None or not self._user_session.is_project_restricted():
            return None
        return tuple(sorted(self._user_session.project_ids_for(permission)))

    def _require_lookup_reader(self) -> FinanceLookupReader:
        if self._lookup_reader is None:
            raise RuntimeError("Finance Lookup Reader is not configured.")
        return self._lookup_reader

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
        can_manage = self._has_project_permission(project_id, "budget.manage")
        can_request_approval = self._has_project_permission(
            project_id, "approval.request"
        )
        can_decide = self._has_project_permission(project_id, "approval.decide")
        can_close = self._has_project_permission(project_id, "budget.approve")
        principal = getattr(self._user_session, "principal", None)
        principal_id = str(getattr(principal, "user_id", "") or "")
        has_open = versions.has_open_version
        versions = replace(
            versions,
            items=tuple(
                replace(
                    item,
                    can_edit=can_manage and item.status == "draft",
                    can_delete=can_manage and item.status == "draft",
                    can_add_line=can_manage and item.status == "draft",
                    can_submit=(
                        can_manage and item.status == "draft" and item.line_count > 0
                    ),
                    can_request_approval=(
                        can_request_approval
                        and item.status == "submitted"
                        and not item.approval_request_id
                    ),
                    can_approve=(
                        can_decide
                        and bool(item.approval_request_id)
                        and bool(principal_id)
                        and item.approval_requested_by_user_id != principal_id
                    ),
                    can_reject=(
                        can_decide
                        and bool(item.approval_request_id)
                        and bool(principal_id)
                        and item.approval_requested_by_user_id != principal_id
                    ),
                    can_create_successor=(
                        can_manage and item.status == "approved" and not has_open
                    ),
                    can_close=can_close and item.status == "approved",
                )
                for item in versions.items
            ),
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
        lines = replace(
            lines,
            items=tuple(
                replace(
                    item,
                    can_edit=can_manage and item.budget_status == "draft",
                    can_delete=can_manage and item.budget_status == "draft",
                )
                for item in lines.items
            ),
        )
        return FinanceBudgetWorkspaceFacts(
            selected_budget_id=normalized_budget_id,
            versions=versions,
            lines=lines,
            show_create_version=can_manage,
            can_create_version=can_manage and not has_open,
            create_version_disabled_reason=(
                "A Draft or Submitted budget is already open. Complete its "
                "workflow or delete the Draft before creating another version."
                if can_manage and has_open
                else ""
            ),
        )

    def _has_project_permission(self, project_id: str, permission: str) -> bool:
        session = self._user_session
        return bool(
            session is not None
            and session.has_permission(permission)
            and session.has_project_permission(project_id, permission)
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
        can_manage = self._has_project_permission(project_id, "forecast.manage")
        can_request = self._has_project_permission(project_id, "approval.request")
        can_decide = self._has_project_permission(project_id, "approval.decide")
        principal = getattr(self._user_session, "principal", None)
        principal_id = str(getattr(principal, "user_id", "") or "")
        versions = replace(
            versions,
            items=tuple(
                replace(
                    item,
                    can_submit=can_manage and item.status == "draft" and item.line_count > 0,
                    can_request_approval=(
                        can_request
                        and item.status == "submitted"
                        and not item.approval_request_id
                    ),
                    can_approve=(
                        can_decide
                        and bool(item.approval_request_id)
                        and bool(principal_id)
                        and item.approval_requested_by_user_id != principal_id
                    ),
                    can_reject=(
                        can_decide
                        and bool(item.approval_request_id)
                        and bool(principal_id)
                        and item.approval_requested_by_user_id != principal_id
                    ),
                )
                for item in versions.items
            ),
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
            show_generate=can_manage,
            can_generate=can_manage and not versions.has_open_version,
            generate_disabled_reason=(
                "Complete the open Forecast workflow before generating another revision."
                if can_manage
                and versions.has_open_version
                else ""
            ),
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
        can_manage = self._has_project_permission(
            project_id, "financial_change.manage"
        )
        can_request = self._has_project_permission(project_id, "approval.request")
        can_decide = self._has_project_permission(project_id, "approval.decide")
        principal = getattr(self._user_session, "principal", None)
        principal_id = str(getattr(principal, "user_id", "") or "")
        if selected is not None:
            is_draft = selected.status == "draft"
            is_pending = (
                selected.status == "pending_approval"
                and selected.approval_status.upper() == "PENDING"
                and bool(selected.approval_request_id)
            )
            can_decide_selected = (
                can_decide
                and is_pending
                and bool(principal_id)
                and selected.approval_requested_by_user_id != principal_id
            )
            selected = replace(
                selected,
                can_edit=can_manage and is_draft,
                can_add_impact=can_manage and is_draft,
                can_submit=(
                    can_manage
                    and can_request
                    and is_draft
                    and selected.impact_count > 0
                ),
                can_approve=can_decide_selected,
                can_reject=can_decide_selected,
            )
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
        impacts = replace(
            impacts,
            items=tuple(
                replace(
                    item,
                    can_edit=bool(selected and selected.can_edit),
                    can_remove=bool(selected and selected.can_edit),
                )
                for item in impacts.items
            ),
        )
        return FinanceChangeWorkspaceFacts(
            selected_change_id=resolved_id,
            selected_change=selected,
            changes=changes,
            impacts=impacts,
            can_create=can_manage,
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

    def get_accounting_statuses(
        self,
        project_id: str,
        *,
        request: AccountingStatusQuery | None = None,
    ) -> FinancePageFacts[AccountingStatusFact]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project Accounting outcomes",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project Accounting outcomes",
        )
        if self._billing_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Finance Billing Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project Accounting outcomes"
        )
        return self._billing_reader.list_accounting_statuses(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request or AccountingStatusQuery(),
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
