from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupPageFacts,
    FinanceLookupQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    FinanceRateWorkspaceFacts,
    RateCardRequest,
    RateLineRequest,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class RateCardsWorkspaceQueries:
    def search_rate_resources(
        self, project_id: str, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_rate_lookup(project_id, "search Rate Card resources")
        return self._require_lookup_reader().search_rate_resources(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            request=request,
        )

    def search_rate_departments(
        self, project_id: str, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_rate_lookup(project_id, "search Rate Card departments")
        return self._require_lookup_reader().search_rate_departments(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            request=request,
        )

    def _require_rate_lookup(self, project_id: str, operation: str):
        require_permission(self._user_session, "finance.manage", operation_label=operation)
        require_project_permission(
            self._user_session, project_id, "finance.manage", operation_label=operation
        )
        require_permission(
            self._user_session, "finance.read_sensitive", operation_label=operation
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance lookup scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
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
        can_manage = self._has_project_permission(project_id, "finance.manage")
        cards = replace(
            cards,
            items=tuple(
                replace(
                    item,
                    can_edit=can_manage and item.is_active,
                    can_deactivate=can_manage and item.is_active,
                    can_add_line=can_manage and item.is_active,
                )
                for item in cards.items
            ),
        )
        if selected is not None:
            selected = replace(
                selected,
                can_edit=can_manage and selected.is_active,
                can_deactivate=can_manage and selected.is_active,
                can_add_line=can_manage and selected.is_active,
            )
        lines = replace(
            lines,
            items=tuple(
                replace(
                    item,
                    can_edit=can_manage and item.is_active,
                    can_deactivate=can_manage and item.is_active,
                )
                for item in lines.items
            ),
        )
        return FinanceRateWorkspaceFacts(
            selected_rate_card_id=resolved_id,
            selected_rate_card=selected,
            cards=cards,
            lines=lines,
            can_create_rate_card=can_manage,
        )
