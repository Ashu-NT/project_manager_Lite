from __future__ import annotations

from src.core.modules.project_management.domain.portfolio import PortfolioScenario
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.notifications.domain_events import domain_events


class PortfolioScenarioCommandMixin:
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
        scenario.updated_at = self._utc_now()
        self._scenario_repo.update(scenario)
        self._session.commit()
        domain_events.portfolio_changed.emit(scenario.id)
        return scenario


__all__ = ["PortfolioScenarioCommandMixin"]
