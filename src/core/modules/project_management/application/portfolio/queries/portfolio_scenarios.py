from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.core.modules.project_management.application.resources.resource_load_engine import (
    ResourceLoadEngine,
)
from src.core.modules.project_management.contracts.reads.portfolio.models.scenario_facts import (
    PortfolioScenarioFact,
    PortfolioScenarioFacts,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class PortfolioScenarioQueryMixin:
    def list_scenarios(self) -> list[PortfolioScenario]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio scenarios")
        self._active_portfolio_organization_id(operation_label="view portfolio scenarios")
        return self._scenario_repo.list()

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        require_permission(self._user_session, "portfolio.read", operation_label="evaluate portfolio scenario")
        facts = self._read_scenario_facts((str(scenario_id),))
        scenario = next((row for row in facts.scenarios if row.id == scenario_id), None)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        capacities = self._project_capacity_totals(facts)
        return self._evaluate_scenario_fact(
            scenario,
            facts=facts,
            capacity_by_project=capacities,
            available_capacity_percent=self._available_capacity(facts),
        )

    def compare_scenarios(
        self,
        base_scenario_id: str,
        candidate_scenario_id: str,
    ) -> PortfolioScenarioComparison:
        require_permission(self._user_session, "portfolio.read", operation_label="compare portfolio scenarios")
        normalized_base = str(base_scenario_id or "").strip()
        normalized_candidate = str(candidate_scenario_id or "").strip()
        if not normalized_base or not normalized_candidate:
            raise ValidationError("Select two scenarios to compare.", code="PORTFOLIO_COMPARISON_REQUIRED")
        if normalized_base == normalized_candidate:
            raise ValidationError(
                "Choose two different scenarios to compare.",
                code="PORTFOLIO_COMPARISON_DUPLICATE",
            )

        facts = self._read_scenario_facts((normalized_base, normalized_candidate))
        scenarios = {scenario.id: scenario for scenario in facts.scenarios}
        base_scenario = scenarios.get(normalized_base)
        candidate_scenario = scenarios.get(normalized_candidate)
        if base_scenario is None or candidate_scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")

        capacities = self._project_capacity_totals(facts)
        available_capacity = self._available_capacity(facts)
        base_evaluation = self._evaluate_scenario_fact(
            base_scenario,
            facts=facts,
            capacity_by_project=capacities,
            available_capacity_percent=available_capacity,
        )
        candidate_evaluation = self._evaluate_scenario_fact(
            candidate_scenario,
            facts=facts,
            capacity_by_project=capacities,
            available_capacity_percent=available_capacity,
        )

        accessible_projects = {project.id: project for project in facts.projects}
        intake_by_id = {item.id: item for item in facts.intake_items}
        base_projects, base_intake = self._scenario_selection(
            base_scenario,
            accessible_projects=accessible_projects,
            intake_by_id=intake_by_id,
        )
        candidate_projects, candidate_intake = self._scenario_selection(
            candidate_scenario,
            accessible_projects=accessible_projects,
            intake_by_id=intake_by_id,
        )
        base_project_names = {project.name for project in base_projects}
        candidate_project_names = {project.name for project in candidate_projects}
        base_intake_titles = {item.title for item in base_intake}
        candidate_intake_titles = {item.title for item in candidate_intake}

        comparison = PortfolioScenarioComparison(
            base_scenario_id=base_scenario.id,
            base_scenario_name=base_scenario.name,
            candidate_scenario_id=candidate_scenario.id,
            candidate_scenario_name=candidate_scenario.name,
            base_evaluation=base_evaluation,
            candidate_evaluation=candidate_evaluation,
            budget_delta=candidate_evaluation.total_budget - base_evaluation.total_budget,
            capacity_delta_percent=(
                candidate_evaluation.total_capacity_percent - base_evaluation.total_capacity_percent
            ),
            intake_score_delta=candidate_evaluation.intake_composite_score - base_evaluation.intake_composite_score,
            selected_projects_delta=candidate_evaluation.selected_projects - base_evaluation.selected_projects,
            selected_intake_items_delta=(
                candidate_evaluation.selected_intake_items - base_evaluation.selected_intake_items
            ),
            added_project_names=sorted(candidate_project_names - base_project_names),
            removed_project_names=sorted(base_project_names - candidate_project_names),
            added_intake_titles=sorted(candidate_intake_titles - base_intake_titles),
            removed_intake_titles=sorted(base_intake_titles - candidate_intake_titles),
        )
        comparison.summary = self._build_comparison_summary(comparison)
        return comparison

    def _read_scenario_facts(self, scenario_ids: tuple[str, ...]) -> PortfolioScenarioFacts:
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="evaluate portfolio scenarios"
        )
        accessible_project_ids = tuple(project.id for project in self._accessible_projects())
        return self._scenario_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            scenario_ids=tuple(dict.fromkeys(scenario_ids)),
            accessible_project_ids=accessible_project_ids,
        )

    def _project_capacity_totals(self, facts: PortfolioScenarioFacts) -> dict[str, float]:
        working_dates = self._scenario_working_dates(facts)
        tasks_by_project: dict[str, list[object]] = {}
        for task in facts.tasks:
            tasks_by_project.setdefault(task.project_id, []).append(task)
        assignments_by_project: dict[str, list[object]] = {}
        task_projects = {task.id: task.project_id for task in facts.tasks}
        for assignment in facts.assignments:
            project_id = task_projects.get(assignment.task_id)
            if project_id is not None:
                assignments_by_project.setdefault(project_id, []).append(assignment)
        return {
            project.id: sum(
                row.total_allocation_percent
                for row in ResourceLoadEngine.calculate(
                    tasks=tasks_by_project.get(project.id, ()),
                    assignments=assignments_by_project.get(project.id, ()),
                    resources=facts.resources,
                    working_dates=working_dates,
                )
            )
            for project in facts.projects
        }

    def _scenario_working_dates(self, facts: PortfolioScenarioFacts) -> frozenset[date]:
        ranges = [
            (min(task.start_date, task.end_date), max(task.start_date, task.end_date))
            for task in facts.tasks
            if task.start_date and task.end_date
        ]
        if not ranges:
            return frozenset()
        start = min(row_start for row_start, _row_end in ranges)
        end = max(row_end for _row_start, row_end in ranges)
        bulk_loader = getattr(self._calendar, "working_day_dates_between", None)
        if callable(bulk_loader):
            return frozenset(bulk_loader(start, end))
        working: set[date] = set()
        current = start
        while current <= end:
            if self._calendar.is_working_day(current):
                working.add(current)
            current += timedelta(days=1)
        return frozenset(working)

    def _evaluate_scenario_fact(
        self,
        scenario: PortfolioScenarioFact,
        *,
        facts: PortfolioScenarioFacts,
        capacity_by_project: dict[str, float],
        available_capacity_percent: float,
    ) -> PortfolioScenarioEvaluation:
        selected_projects, selected_intake = self._scenario_selection(
            scenario,
            accessible_projects={project.id: project for project in facts.projects},
            intake_by_id={item.id: item for item in facts.intake_items},
        )
        total_budget = sum(
            (project.approved_budget for project in selected_projects),
            Decimal("0"),
        )
        total_budget += sum(
            (item.requested_budget for item in selected_intake),
            Decimal("0"),
        )
        total_capacity_percent = sum(
            capacity_by_project.get(project.id, 0.0) for project in selected_projects
        )
        total_capacity_percent += sum(
            item.requested_capacity_percent for item in selected_intake
        )
        capacity_limit = (
            scenario.capacity_limit_percent
            if scenario.capacity_limit_percent is not None
            else available_capacity_percent
        )
        over_budget = scenario.budget_limit is not None and total_budget > scenario.budget_limit
        over_capacity = total_capacity_percent > float(capacity_limit or 0.0)
        intake_score = sum(item.composite_score for item in selected_intake)
        summary = self._build_evaluation_summary(
            over_budget=over_budget,
            over_capacity=over_capacity,
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity_percent,
            capacity_limit=float(capacity_limit or 0.0),
            selected_projects=len(selected_projects),
            selected_intake=len(selected_intake),
        )
        return PortfolioScenarioEvaluation(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            selected_projects=len(selected_projects),
            selected_intake_items=len(selected_intake),
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity_percent,
            capacity_limit_percent=capacity_limit,
            available_capacity_percent=available_capacity_percent,
            intake_composite_score=intake_score,
            over_budget=over_budget,
            over_capacity=over_capacity,
            summary=summary,
        )

    @staticmethod
    def _available_capacity(facts: PortfolioScenarioFacts) -> float:
        return sum(resource.capacity_percent for resource in facts.resources if resource.is_active)


__all__ = ["PortfolioScenarioQueryMixin"]
