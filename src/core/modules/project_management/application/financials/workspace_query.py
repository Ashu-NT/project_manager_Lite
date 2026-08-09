from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.repositories.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.contracts.repositories.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.domain.financials.configuration import (
    ProjectFinancialProfile,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


@dataclass(frozen=True, slots=True)
class FinanceBudgetVersionRead:
    id: str
    name: str
    status: str
    revision: int
    row_version: int
    currency_code: str
    line_count: int
    total_amount: Decimal
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    notes: str


@dataclass(frozen=True, slots=True)
class FinanceBudgetLineRead:
    id: str
    budget_id: str
    budget_name: str
    budget_revision: int
    budget_status: str
    description: str
    cost_code: str
    cost_code_name: str
    task_name: str
    wbs_code: str
    amount: Decimal
    currency_code: str


@dataclass(frozen=True, slots=True)
class FinanceRateCardRead:
    id: str
    name: str
    scope: str
    is_active: bool
    is_legacy: bool
    version: int
    line_count: int


@dataclass(frozen=True, slots=True)
class FinanceRateLineRead:
    id: str
    rate_card_id: str
    rate_card_name: str
    card_scope: str
    rate_type: str
    origin: str
    rate_amount: Decimal
    rate_currency: str
    unit: str
    resource_name: str
    role: str
    skill_code: str
    department_id: str
    effective_from: date | None
    effective_to: date | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class FinancePlannedCostVersionRead:
    id: str
    revision: int
    status: str
    currency_code: str
    as_of: date
    calculated_by: str
    calculated_at: datetime
    line_count: int
    total_hours: Decimal
    total_amount: Decimal
    rates_complete: bool
    allocations_complete: bool
    cost_codes_complete: bool
    unresolved_rate_count: int
    partially_allocated_resource_count: int
    unclassified_line_count: int


@dataclass(frozen=True, slots=True)
class FinancePlannedCostLineRead:
    id: str
    version_id: str
    version_revision: int
    version_status: str
    task_name: str
    wbs_code: str
    resource_name: str
    cost_code: str
    cost_code_name: str
    planned_hours: Decimal
    rate_amount: Decimal
    amount: Decimal
    currency_code: str
    rate_card_id: str
    rate_card_version: int


@dataclass(frozen=True, slots=True)
class ProjectFinanceWorkspaceRead:
    project_id: str
    profile: ProjectFinancialProfile | None
    default_cost_code: str
    budget_versions: tuple[FinanceBudgetVersionRead, ...]
    budget_lines: tuple[FinanceBudgetLineRead, ...]
    rate_cards: tuple[FinanceRateCardRead, ...]
    rate_lines: tuple[FinanceRateLineRead, ...]
    planned_cost_versions: tuple[FinancePlannedCostVersionRead, ...]
    planned_cost_lines: tuple[FinancePlannedCostLineRead, ...]


class ProjectFinanceWorkspaceQuery:
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
        user_session=None,
    ) -> None:
        self._profile_repo = profile_repo
        self._cost_code_repo = cost_code_repo
        self._budget_repo = budget_repo
        self._rate_card_repo = rate_card_repo
        self._planned_cost_repo = planned_cost_repo
        self._task_repo = task_repo
        self._resource_repo = resource_repo
        self._user_session = user_session

    def get(self, project_id: str) -> ProjectFinanceWorkspaceRead:
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

        profile = self._profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        cost_codes = self._cost_code_repo.list(include_inactive=True)
        cost_code_by_id = {item.id: item for item in cost_codes}
        tasks = self._task_repo.list_by_project(project_id)
        task_by_id = {item.id: item for item in tasks}
        resources = self._resource_repo.list()
        resource_by_id = {item.id: item for item in resources}

        budgets = self._budget_repo.list_for_project(project_id, include_superseded=True)
        budget_by_id = {item.id: item for item in budgets}
        budget_lines = self._budget_repo.list_lines_for_project(project_id)
        budget_lines_by_id: dict[str, list] = {}
        for line in budget_lines:
            budget_lines_by_id.setdefault(line.budget_id, []).append(line)

        cards = self._rate_card_repo.list_visible_for_project(
            project_id, include_inactive=True
        )
        card_by_id = {item.id: item for item in cards}
        rate_lines = self._rate_card_repo.list_lines_for_cards(
            tuple(card_by_id), include_inactive=True
        )
        rate_lines_by_id: dict[str, list] = {}
        for line in rate_lines:
            rate_lines_by_id.setdefault(line.rate_card_id, []).append(line)

        planned_versions = self._planned_cost_repo.list_for_project(project_id)
        planned_version_by_id = {item.id: item for item in planned_versions}
        planned_lines = self._planned_cost_repo.list_lines_for_project(project_id)
        planned_lines_by_id: dict[str, list] = {}
        for line in planned_lines:
            planned_lines_by_id.setdefault(line.version_id, []).append(line)

        default_code = cost_code_by_id.get(
            profile.default_cost_code_id if profile else ""
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
                    line_count=len(budget_lines_by_id.get(budget.id, ())),
                    total_amount=sum(
                        (line.amount for line in budget_lines_by_id.get(budget.id, ())),
                        Decimal("0"),
                    ),
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
            rate_cards=tuple(
                FinanceRateCardRead(
                    id=card.id,
                    name=card.name,
                    scope="organization" if card.is_organization_wide else "project",
                    is_active=card.is_active,
                    is_legacy=card.is_legacy,
                    version=card.version,
                    line_count=len(rate_lines_by_id.get(card.id, ())),
                )
                for card in cards
            ),
            rate_lines=tuple(
                self._rate_line_read(line, card_by_id, resource_by_id)
                for line in rate_lines
                if line.rate_card_id in card_by_id
            ),
            planned_cost_versions=tuple(
                FinancePlannedCostVersionRead(
                    id=version.id,
                    revision=version.revision,
                    status=version.status.value,
                    currency_code=version.currency_code,
                    as_of=version.as_of,
                    calculated_by=version.calculated_by,
                    calculated_at=version.calculated_at,
                    line_count=len(planned_lines_by_id.get(version.id, ())),
                    total_hours=sum(
                        (line.planned_hours for line in planned_lines_by_id.get(version.id, ())),
                        Decimal("0"),
                    ),
                    total_amount=sum(
                        (line.amount for line in planned_lines_by_id.get(version.id, ())),
                        Decimal("0"),
                    ),
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
