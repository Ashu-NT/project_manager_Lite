from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinanceBudgetWorkspaceFacts,
    FinancePageFacts,
    FinancePageRequest,
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


class BudgetsWorkspaceQueries:
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
