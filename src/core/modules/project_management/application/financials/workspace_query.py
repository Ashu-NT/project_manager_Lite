from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.application.financials.workspace_models import (
    FinanceBudgetLineRead,
    FinanceBudgetVersionRead,
    FinancePlannedCostLineRead,
    FinancePlannedCostVersionRead,
    FinanceRateCardRead,
    FinanceRateLineRead,
    ProjectFinanceWorkspaceRead,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.planned_costs.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
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
        profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        budget_repo: ProjectBudgetRepository,
        rate_card_repo: ProjectRateCardRepository,
        planned_cost_repo: ProjectPlannedCostVersionRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        budget_reader: FinanceBudgetReader | None = None,
        planned_cost_reader: FinancePlannedCostReader | None = None,
        forecast_reader: FinanceForecastReader | None = None,
        rate_reader: FinanceRateReader | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._profile_repo = profile_repo
        self._cost_code_repo = cost_code_repo
        self._budget_repo = budget_repo
        self._rate_card_repo = rate_card_repo
        self._planned_cost_repo = planned_cost_repo
        self._task_repo = task_repo
        self._resource_repo = resource_repo
        self._budget_reader = budget_reader
        self._planned_cost_reader = planned_cost_reader
        self._forecast_reader = forecast_reader
        self._rate_reader = rate_reader
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

    def get(
        self,
        project_id: str,
        *,
        budget_line_page: int = 1,
        rate_line_page: int = 1,
        planned_cost_line_page: int = 1,
        page_size: int = 50,
        include_profile_details: bool = True,
        include_budgets: bool = True,
        include_rates: bool = True,
        include_planned_costs: bool = True,
    ) -> ProjectFinanceWorkspaceRead:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view project finance workspace",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view project finance workspace",
        )

        budget_page = PageRequest(page=budget_line_page, page_size=page_size)
        rate_page = PageRequest(page=rate_line_page, page_size=page_size)
        planned_page = PageRequest(page=planned_cost_line_page, page_size=page_size)

        profile = self._profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        needs_cost_codes = (
            include_profile_details or include_budgets or include_planned_costs
        )
        needs_tasks = include_budgets or include_planned_costs
        needs_resources = include_rates or include_planned_costs
        cost_codes = (
            self._cost_code_repo.list(include_inactive=True)
            if needs_cost_codes
            else []
        )
        cost_code_by_id = {item.id: item for item in cost_codes}
        tasks = self._task_repo.list_by_project(project_id) if needs_tasks else []
        task_by_id = {item.id: item for item in tasks}
        resources = self._resource_repo.list() if needs_resources else []
        resource_by_id = {item.id: item for item in resources}

        budgets = (
            self._budget_repo.list_for_project(project_id, include_superseded=True)
            if include_budgets
            else []
        )
        budget_by_id = {item.id: item for item in budgets}
        budget_line_summaries = (
            self._budget_repo.summarize_lines_for_project(project_id)
            if include_budgets
            else {}
        )
        budget_line_total = sum(item[0] for item in budget_line_summaries.values())
        budget_page.page = normalize_page_for_total(
            page=budget_page.page,
            page_size=budget_page.page_size,
            total=budget_line_total,
        )
        budget_lines = (
            self._budget_repo.list_lines_for_project(
                project_id, offset=budget_page.offset, limit=budget_page.limit
            )
            if include_budgets
            else []
        )
        cards = (
            self._rate_card_repo.list_visible_for_project(
                project_id, include_inactive=True
            )
            if include_rates
            else []
        )
        card_by_id = {item.id: item for item in cards}
        rate_line_counts = (
            self._rate_card_repo.count_lines_by_card(
                tuple(card_by_id), include_inactive=True
            )
            if card_by_id
            else {}
        )
        rate_line_total = sum(rate_line_counts.values())
        rate_page.page = normalize_page_for_total(
            page=rate_page.page,
            page_size=rate_page.page_size,
            total=rate_line_total,
        )
        rate_lines = (
            self._rate_card_repo.list_lines_for_cards(
                tuple(card_by_id),
                include_inactive=True,
                offset=rate_page.offset,
                limit=rate_page.limit,
            )
            if card_by_id
            else []
        )
        planned_versions = (
            self._planned_cost_repo.list_for_project(project_id)
            if include_planned_costs
            else []
        )
        planned_version_by_id = {item.id: item for item in planned_versions}
        planned_line_summaries = (
            self._planned_cost_repo.summarize_lines_for_project(project_id)
            if include_planned_costs
            else {}
        )
        planned_line_total = sum(item[0] for item in planned_line_summaries.values())
        planned_page.page = normalize_page_for_total(
            page=planned_page.page,
            page_size=planned_page.page_size,
            total=planned_line_total,
        )
        planned_lines = (
            self._planned_cost_repo.list_lines_for_project(
                project_id, offset=planned_page.offset, limit=planned_page.limit
            )
            if include_planned_costs
            else []
        )
        default_code = cost_code_by_id.get(
            profile.default_cost_code_id
        )
        return ProjectFinanceWorkspaceRead(
            project_id=project_id,
            profile=profile,
            default_cost_code=(
                f"{default_code.code} - {default_code.name}" if default_code else ""
            ),
            budget_versions=tuple(
                FinanceBudgetVersionRead(
                    id=budget.id,
                    name=budget.name,
                    status=budget.status.value,
                    revision=budget.revision,
                    row_version=budget.row_version,
                    currency_code=budget.currency_code,
                    line_count=budget_line_summaries.get(
                        budget.id, (0, Decimal("0"))
                    )[0],
                    total_amount=budget_line_summaries.get(
                        budget.id, (0, Decimal("0"))
                    )[1],
                    submitted_by=budget.submitted_by,
                    submitted_at=budget.submitted_at,
                    approved_by=budget.approved_by,
                    approved_at=budget.approved_at,
                    notes=budget.notes,
                )
                for budget in budgets
            ),
            budget_lines=tuple(
                self._budget_line_read(line, budget_by_id, cost_code_by_id, task_by_id)
                for line in budget_lines
                if line.budget_id in budget_by_id
            ),
            budget_line_page=budget_page.page,
            budget_line_page_size=budget_page.page_size,
            budget_line_total=budget_line_total,
            rate_cards=tuple(
                FinanceRateCardRead(
                    id=card.id,
                    name=card.name,
                    scope="organization" if card.is_organization_wide else "project",
                    is_active=card.is_active,
                    is_legacy=card.is_legacy,
                    version=card.version,
                    line_count=rate_line_counts.get(card.id, 0),
                )
                for card in cards
            ),
            rate_lines=tuple(
                self._rate_line_read(line, card_by_id, resource_by_id)
                for line in rate_lines
                if line.rate_card_id in card_by_id
            ),
            rate_line_page=rate_page.page,
            rate_line_page_size=rate_page.page_size,
            rate_line_total=rate_line_total,
            planned_cost_versions=tuple(
                FinancePlannedCostVersionRead(
                    id=version.id,
                    revision=version.revision,
                    status=version.status.value,
                    currency_code=version.currency_code,
                    as_of=version.as_of,
                    calculated_by=version.calculated_by,
                    calculated_at=version.calculated_at,
                    line_count=planned_line_summaries.get(
                        version.id, (0, Decimal("0"), Decimal("0"))
                    )[0],
                    total_hours=planned_line_summaries.get(
                        version.id, (0, Decimal("0"), Decimal("0"))
                    )[1],
                    total_amount=planned_line_summaries.get(
                        version.id, (0, Decimal("0"), Decimal("0"))
                    )[2],
                    rates_complete=version.rates_complete,
                    allocations_complete=version.allocations_complete,
                    cost_codes_complete=version.cost_codes_complete,
                    unresolved_rate_count=version.unresolved_rate_count,
                    partially_allocated_resource_count=(
                        version.partially_allocated_resource_count
                    ),
                    unclassified_line_count=version.unclassified_line_count,
                )
                for version in planned_versions
            ),
            planned_cost_lines=tuple(
                self._planned_line_read(
                    line,
                    planned_version_by_id,
                    cost_code_by_id,
                    task_by_id,
                    resource_by_id,
                )
                for line in planned_lines
                if line.version_id in planned_version_by_id
            ),
            planned_cost_line_page=planned_page.page,
            planned_cost_line_page_size=planned_page.page_size,
            planned_cost_line_total=planned_line_total,
        )

    @staticmethod
    def _budget_line_read(line, budgets, cost_codes, tasks) -> FinanceBudgetLineRead:
        budget = budgets[line.budget_id]
        cost_code = cost_codes.get(line.cost_code_id)
        task = tasks.get(line.task_id or "")
        return FinanceBudgetLineRead(
            id=line.id,
            budget_id=budget.id,
            budget_name=budget.name,
            budget_revision=budget.revision,
            budget_status=budget.status.value,
            description=line.description,
            cost_code=cost_code.code if cost_code else line.cost_code_id,
            cost_code_name=cost_code.name if cost_code else "",
            task_name=task.name if task else "Unassigned",
            wbs_code=task.wbs_code if task else "",
            amount=line.amount,
            currency_code=line.currency_code,
        )

    @staticmethod
    def _rate_line_read(line, cards, resources) -> FinanceRateLineRead:
        card = cards[line.rate_card_id]
        resource = resources.get(line.resource_id or "")
        return FinanceRateLineRead(
            id=line.id,
            rate_card_id=card.id,
            rate_card_name=card.name,
            card_scope="organization" if card.is_organization_wide else "project",
            rate_type=line.rate_type.value,
            origin=line.origin.value,
            rate_amount=line.rate_amount,
            rate_currency=line.rate_currency,
            unit=line.unit,
            resource_name=resource.name if resource else "",
            role=line.role or "",
            skill_code=line.skill_code or "",
            department_id=line.department_id or "",
            effective_from=line.effective_from,
            effective_to=line.effective_to,
            is_active=line.is_active,
        )

    @staticmethod
    def _planned_line_read(
        line, versions, cost_codes, tasks, resources
    ) -> FinancePlannedCostLineRead:
        version = versions[line.version_id]
        cost_code = cost_codes.get(line.cost_code_id)
        task = tasks.get(line.task_id)
        resource = resources.get(line.resource_id)
        return FinancePlannedCostLineRead(
            id=line.id,
            version_id=version.id,
            version_revision=version.revision,
            version_status=version.status.value,
            task_name=task.name if task else line.task_id,
            wbs_code=task.wbs_code if task else "",
            resource_name=resource.name if resource else line.resource_id,
            cost_code=cost_code.code if cost_code else line.cost_code_id,
            cost_code_name=cost_code.name if cost_code else "",
            planned_hours=line.planned_hours,
            rate_amount=line.rate_amount,
            amount=line.amount,
            currency_code=line.currency_code,
            rate_card_id=line.rate_card_id,
            rate_card_version=line.rate_card_version,
        )


__all__ = [
    "FinanceBudgetLineRead",
    "FinanceBudgetVersionRead",
    "FinancePlannedCostLineRead",
    "FinancePlannedCostVersionRead",
    "FinanceRateCardRead",
    "FinanceRateLineRead",
    "ProjectFinanceWorkspaceQuery",
    "ProjectFinanceWorkspaceRead",
]
