from __future__ import annotations

from datetime import datetime, timezone

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from core.modules.project_management.domain.portfolio import (
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
)
from src.core.platform.auth.authorization import require_permission


class PortfolioScenarioMixin:
    def list_scenarios(self) -> list[PortfolioScenario]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio scenarios")
        return self._scenario_repo.list_all()

    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: float | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio scenario")
        scenario = PortfolioScenario.create(
            name=self._require_non_empty(name, "Scenario name"),
            budget_limit=(None if budget_limit is None else self._non_negative(budget_limit, "Budget limit")),
            capacity_limit_percent=(
                None
                if capacity_limit_percent is None
                else self._non_negative(capacity_limit_percent, "Capacity limit")
            ),
            project_ids=self._validate_project_ids(project_ids or []),
            intake_item_ids=self._validate_intake_ids(intake_item_ids or []),
            notes=notes,
        )
        self._scenario_repo.add(scenario)
        self._session.commit()
        domain_events.portfolio_changed.emit(scenario.id)
        return scenario

    def update_scenario(self, scenario_id: str, **changes) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio scenario")
        scenario = self._scenario_repo.get(scenario_id)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        if "name" in changes and changes["name"] is not None:
            scenario.name = self._require_non_empty(changes["name"], "Scenario name")
        if "budget_limit" in changes:
            scenario.budget_limit = (
                None
                if changes["budget_limit"] is None
                else self._non_negative(changes["budget_limit"], "Budget limit")
            )
        if "capacity_limit_percent" in changes:
            scenario.capacity_limit_percent = (
                None
                if changes["capacity_limit_percent"] is None
                else self._non_negative(changes["capacity_limit_percent"], "Capacity limit")
            )
        if "project_ids" in changes and changes["project_ids"] is not None:
            scenario.project_ids = self._validate_project_ids(list(changes["project_ids"]))
        if "intake_item_ids" in changes and changes["intake_item_ids"] is not None:
            scenario.intake_item_ids = self._validate_intake_ids(list(changes["intake_item_ids"]))
        if "notes" in changes and changes["notes"] is not None:
            scenario.notes = (changes["notes"] or "").strip()
        scenario.updated_at = datetime.now(timezone.utc)
        self._scenario_repo.update(scenario)
        self._session.commit()
        domain_events.portfolio_changed.emit(scenario.id)
        return scenario

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        require_permission(self._user_session, "portfolio.read", operation_label="evaluate portfolio scenario")
        scenario = self._scenario_repo.get(scenario_id)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        projects = {project.id: project for project in self._accessible_projects()}
        intake_by_id = {item.id: item for item in self._intake_repo.list_all()}
        selected_projects, selected_intake = self._scenario_selection(
            scenario,
            accessible_projects=projects,
            intake_by_id=intake_by_id,
        )
        total_budget = sum(float(getattr(project, "planned_budget", 0.0) or 0.0) for project in selected_projects)
        total_budget += sum(float(item.requested_budget or 0.0) for item in selected_intake)

        total_capacity_percent = sum(
            sum(
                float(row.total_allocation_percent or 0.0)
                for row in self._reporting.get_resource_load_summary(project.id)
            )
            for project in selected_projects
        )
        total_capacity_percent += sum(
            float(item.requested_capacity_percent or 0.0) for item in selected_intake
        )

        available_capacity_percent = sum(
            float(getattr(resource, "capacity_percent", 0.0) or 0.0)
            for resource in self._resource_repo.list_all()
            if bool(getattr(resource, "is_active", True))
        )
        capacity_limit = (
            scenario.capacity_limit_percent
            if scenario.capacity_limit_percent is not None
            else available_capacity_percent
        )
        over_budget = scenario.budget_limit is not None and total_budget > float(scenario.budget_limit)
        over_capacity = total_capacity_percent > float(capacity_limit or 0.0)
        intake_score = sum(int(item.composite_score or 0) for item in selected_intake)
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

        base_scenario = self._scenario_repo.get(normalized_base)
        candidate_scenario = self._scenario_repo.get(normalized_candidate)
        if base_scenario is None or candidate_scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")

        base_evaluation = self.evaluate_scenario(base_scenario.id)
        candidate_evaluation = self.evaluate_scenario(candidate_scenario.id)

        accessible_projects = {project.id: project for project in self._accessible_projects()}
        intake_by_id = {item.id: item for item in self._intake_repo.list_all()}
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

    def _validate_project_ids(self, project_ids: list[str]) -> list[str]:
        known_ids = {project.id for project in self._accessible_projects()}
        invalid = [project_id for project_id in project_ids if project_id not in known_ids]
        if invalid:
            raise ValidationError(
                f"Scenario contains unknown or inaccessible project ids: {', '.join(invalid)}.",
                code="PORTFOLIO_PROJECT_SCOPE_INVALID",
            )
        return sorted({project_id for project_id in project_ids if project_id})

    def _validate_intake_ids(self, intake_item_ids: list[str]) -> list[str]:
        known_ids = {item.id for item in self._intake_repo.list_all()}
        invalid = [item_id for item_id in intake_item_ids if item_id not in known_ids]
        if invalid:
            raise ValidationError(
                f"Scenario contains unknown intake item ids: {', '.join(invalid)}.",
                code="PORTFOLIO_INTAKE_SCOPE_INVALID",
            )
        return sorted({item_id for item_id in intake_item_ids if item_id})


__all__ = ["PortfolioScenarioMixin"]
