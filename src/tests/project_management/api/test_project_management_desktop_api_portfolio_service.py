from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_portfolio_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    ProjectStatus,
    TaskStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
    PortfolioRecentAction,
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.tests.project_management.test_project_management_desktop_api_portfolio_fakes import (
    _FakePortfolioServiceBase,
    _FakeProjectService,
)


class _FakePortfolioService(_FakePortfolioServiceBase):
    def list_scenarios(self) -> list[PortfolioScenario]:
        return list(self._scenarios.values())

    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: Decimal | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        scenario = PortfolioScenario(
            id=f"scn-{len(self._scenarios) + 1}",
            name=name,
            organization_id="org-1",
            budget_limit=budget_limit,
            capacity_limit_percent=capacity_limit_percent,
            project_ids=list(project_ids or []),
            intake_item_ids=list(intake_item_ids or []),
            notes=notes,
            created_at=datetime(2026, 5, 2, 9, 0),
            updated_at=datetime(2026, 5, 2, 9, 0),
        )
        self._scenarios[scenario.id] = scenario
        self._append_action("Scenario saved", "Portfolio", scenario.name)
        return scenario

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        scenario = self._scenarios[scenario_id]
        selected_projects = [
            self._project_service.get_project(project_id)
            for project_id in scenario.project_ids
        ]
        selected_items = [
            self._intake_items[item_id]
            for item_id in scenario.intake_item_ids
            if item_id in self._intake_items
        ]
        intake_budget = sum(
            (item.requested_budget for item in selected_items),
            Decimal("0"),
        )
        total_budget = intake_budget
        total_capacity = sum(float(item.requested_capacity_percent or 0.0) for item in selected_items)
        capacity_limit = scenario.capacity_limit_percent
        available_capacity = max(float(capacity_limit or 0.0) - total_capacity, 0.0)
        over_budget = scenario.budget_limit is not None and total_budget > scenario.budget_limit
        over_capacity = capacity_limit is not None and total_capacity > float(capacity_limit)
        return PortfolioScenarioEvaluation(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            selected_projects=len([p for p in selected_projects if p is not None]),
            selected_intake_items=len(selected_items),
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity,
            capacity_limit_percent=capacity_limit,
            available_capacity_percent=available_capacity,
            intake_composite_score=sum(item.composite_score for item in selected_items),
            over_budget=over_budget,
            over_capacity=over_capacity,
            summary="Within limits" if not over_budget and not over_capacity else "Escalation required",
        )

    def compare_scenarios(self, base_scenario_id: str, candidate_scenario_id: str) -> PortfolioScenarioComparison:
        base = self._scenarios[base_scenario_id]
        candidate = self._scenarios[candidate_scenario_id]
        base_eval = self.evaluate_scenario(base_scenario_id)
        candidate_eval = self.evaluate_scenario(candidate_scenario_id)
        base_project_ids = set(base.project_ids)
        candidate_project_ids = set(candidate.project_ids)
        base_intake_ids = set(base.intake_item_ids)
        candidate_intake_ids = set(candidate.intake_item_ids)
        return PortfolioScenarioComparison(
            base_scenario_id=base.id,
            base_scenario_name=base.name,
            candidate_scenario_id=candidate.id,
            candidate_scenario_name=candidate.name,
            base_evaluation=base_eval,
            candidate_evaluation=candidate_eval,
            budget_delta=candidate_eval.total_budget - base_eval.total_budget,
            capacity_delta_percent=candidate_eval.total_capacity_percent - base_eval.total_capacity_percent,
            intake_score_delta=candidate_eval.intake_composite_score - base_eval.intake_composite_score,
            selected_projects_delta=candidate_eval.selected_projects - base_eval.selected_projects,
            selected_intake_items_delta=candidate_eval.selected_intake_items - base_eval.selected_intake_items,
            added_project_names=[
                self._project_service.get_project(pid).name
                for pid in sorted(candidate_project_ids - base_project_ids)
                if self._project_service.get_project(pid) is not None
            ],
            removed_project_names=[
                self._project_service.get_project(pid).name
                for pid in sorted(base_project_ids - candidate_project_ids)
                if self._project_service.get_project(pid) is not None
            ],
            added_intake_titles=[
                self._intake_items[iid].title
                for iid in sorted(candidate_intake_ids - base_intake_ids)
                if iid in self._intake_items
            ],
            removed_intake_titles=[
                self._intake_items[iid].title
                for iid in sorted(base_intake_ids - candidate_intake_ids)
                if iid in self._intake_items
            ],
            summary="Candidate scenario increases scope and portfolio demand.",
        )

    def list_portfolio_heatmap(self) -> list[PortfolioExecutiveRow]:
        rows: list[PortfolioExecutiveRow] = []
        for project in self._project_service.list_projects():
            pressure_label = "Hot" if project.status == ProjectStatus.ON_HOLD else "Stable"
            rows.append(
                PortfolioExecutiveRow(
                    project_id=project.id,
                    project_name=project.name,
                    project_status=project.status.value,
                    late_tasks=1 if pressure_label == "Hot" else 0,
                    critical_tasks=1,
                    peak_utilization_percent=118.0 if pressure_label == "Hot" else 92.0,
                    cost_variance=(
                        Decimal("-8500")
                        if pressure_label == "Hot"
                        else Decimal("2500")
                    ),
                    pressure_score=90 if pressure_label == "Hot" else 40,
                    pressure_label=pressure_label,
                )
            )
        return rows

    def list_project_dependencies(self) -> list[PortfolioProjectDependencyView]:
        rows: list[PortfolioProjectDependencyView] = []
        for dependency in self._dependencies.values():
            predecessor = self._project_service.get_project(dependency.predecessor_project_id)
            successor = self._project_service.get_project(dependency.successor_project_id)
            rows.append(
                PortfolioProjectDependencyView(
                    dependency_id=dependency.id,
                    predecessor_project_id=dependency.predecessor_project_id,
                    predecessor_project_name=getattr(predecessor, "name", dependency.predecessor_project_id),
                    predecessor_project_status=getattr(getattr(predecessor, "status", None), "value", "PLANNED"),
                    successor_project_id=dependency.successor_project_id,
                    successor_project_name=getattr(successor, "name", dependency.successor_project_id),
                    successor_project_status=getattr(getattr(successor, "status", None), "value", "PLANNED"),
                    dependency_type=dependency.dependency_type,
                    summary=dependency.summary,
                    pressure_label="Watch",
                    created_at=dependency.created_at,
                )
            )
        return rows

    def create_project_dependency(
        self,
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> PortfolioProjectDependency:
        dependency = PortfolioProjectDependency(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_project_id=predecessor_project_id,
            successor_project_id=successor_project_id,
            dependency_type=dependency_type,
            summary=summary,
            created_at=datetime(2026, 5, 3, 8, 45),
            updated_at=datetime(2026, 5, 3, 8, 45),
        )
        self._dependencies[dependency.id] = dependency
        self._append_action(
            "Dependency created",
            getattr(self._project_service.get_project(predecessor_project_id), "name", predecessor_project_id),
            summary or dependency.id,
        )
        return dependency

    def remove_project_dependency(self, dependency_id: str) -> None:
        self._dependencies.pop(dependency_id, None)
        self._append_action("Dependency removed", "Portfolio", dependency_id)

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        return list(reversed(self._actions[-limit:]))
