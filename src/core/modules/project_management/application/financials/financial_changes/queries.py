from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_change_facts import (
    FinanceChangeWorkspaceFacts,
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class FinancialChangesWorkspaceQueries:
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
