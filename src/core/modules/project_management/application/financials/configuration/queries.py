from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_setup_facts import (
    FinanceSetupCostCodeQuery,
    FinanceSetupRestrictionQuery,
    FinanceSetupWorkspaceFacts,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class ConfigurationWorkspaceQueries:
    def search_setup_cost_codes(
        self,
        project_id: str,
        *,
        request: FinanceLookupQuery,
        assignment_state: str = "",
        active_only: bool = True,
    ) -> FinanceLookupPageFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="search Financial Setup cost codes",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="search Financial Setup cost codes",
        )
        if self._tenant_context_service is None:
            raise RuntimeError("Finance Setup Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="search Financial Setup cost codes"
        )
        page = self._setup_reader.list_cost_codes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=FinanceSetupCostCodeQuery(
                page=request.normalized_page,
                page_size=request.normalized_page_size,
                search=request.search,
                status="active" if active_only else "",
                assignment_state=assignment_state,
                sort_key="code",
                sort_direction="asc",
            ),
        )
        return FinanceLookupPageFacts(
            items=tuple(
                FinanceLookupOptionFact(id=item.id, label=f"{item.code} - {item.name}")
                for item in page.items
            ),
            total=page.total,
            page=page.page,
            page_size=page.page_size,
        )

    def get_setup_workspace(
        self,
        project_id: str,
        *,
        cost_code_request: FinanceSetupCostCodeQuery | None = None,
        restriction_request: FinanceSetupRestrictionQuery | None = None,
    ) -> FinanceSetupWorkspaceFacts:
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
        can_manage = self._has_project_permission(project_id, "finance.manage")
        can_manage_restrictions = can_manage and setup.cost_code_policy == "restricted"
        cost_codes = self._setup_reader.list_cost_codes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=cost_code_request or FinanceSetupCostCodeQuery(),
        )
        restrictions = self._setup_reader.list_restrictions(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=restriction_request or FinanceSetupRestrictionQuery(),
        )
        cost_codes = replace(
            cost_codes,
            items=tuple(
                replace(
                    item,
                    can_edit=can_manage,
                    can_change_status=can_manage and not item.is_default,
                    can_add_restriction=(
                        can_manage_restrictions and item.is_active and not item.is_assigned
                    ),
                    can_remove_restriction=(
                        can_manage_restrictions and item.is_assigned and not item.is_default
                    ),
                )
                for item in cost_codes.items
            ),
        )
        restrictions = replace(
            restrictions,
            items=tuple(
                replace(
                    item,
                    can_remove=can_manage_restrictions and not item.is_default,
                )
                for item in restrictions.items
            ),
        )
        return FinanceSetupWorkspaceFacts(
            profile=setup,
            cost_codes=cost_codes,
            restrictions=restrictions,
            can_edit_profile=can_manage,
            can_transition_profile=can_manage and setup.status != "closed",
            can_create_cost_code=can_manage,
            can_manage_restrictions=can_manage_restrictions,
        )
