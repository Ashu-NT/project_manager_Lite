from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_forecast_facts import (
    FinanceForecastWorkspaceFacts,
    ForecastLineRequest,
    ForecastVersionRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class ForecastsWorkspaceQueries:
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
