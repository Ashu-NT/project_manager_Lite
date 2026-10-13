from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
    FinancePageRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
    ManualActualDefaultsFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_planned_cost_facts import (
    FinancePlannedCostWorkspaceFacts,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class CostWorkspaceQueries:
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

    def search_manual_actual_resources(
        self, project_id: str, *, request: FinanceLookupQuery
    ) -> FinanceLookupPageFacts:
        scope = self._require_manual_actual_lookup(
            project_id, "search manual actual resources"
        )
        return self._require_lookup_reader().search_rate_resources(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            request=request,
        )

    def resolve_manual_actual_resource(
        self, project_id: str, resource_id: str
    ) -> FinanceLookupOptionFact | None:
        scope = self._require_manual_actual_lookup(
            project_id, "resolve manual actual resource"
        )
        return self._require_lookup_reader().get_resource_option(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=str(resource_id or "").strip(),
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
