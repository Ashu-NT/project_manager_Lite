from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from src.core.modules.project_management.domain.portfolio import PortfolioScenario
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.shared.events.domain_events import domain_events


class PortfolioScenarioCommandMixin:
    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: Decimal | int | str | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio scenario")
        organization_id = self._active_portfolio_organization_id(operation_label="create portfolio scenario")
        scenario = PortfolioScenario.create(
            organization_id=organization_id,
            name=name,
            budget_limit=budget_limit,
            capacity_limit_percent=capacity_limit_percent,
            project_ids=project_ids or [],
            intake_item_ids=intake_item_ids or [],
            notes=notes,
        )
        scenario = replace(
            scenario,
            project_ids=self._validate_project_ids(scenario.project_ids),
            intake_item_ids=self._validate_intake_ids(scenario.intake_item_ids),
        )
        try:
            self._scenario_repo.add(scenario)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.portfolio_changed.emit(scenario.id)
        return scenario

    def update_scenario(self, scenario_id: str, **changes) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio scenario")
        self._active_portfolio_organization_id(operation_label="update portfolio scenario")
        scenario = self._scenario_repo.get(scenario_id)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        candidate = replace(
            scenario,
            name=scenario.name if changes.get("name") is None else changes["name"],
            budget_limit=scenario.budget_limit if "budget_limit" not in changes else changes["budget_limit"],
            capacity_limit_percent=(
                scenario.capacity_limit_percent
                if "capacity_limit_percent" not in changes
                else changes["capacity_limit_percent"]
            ),
            project_ids=(
                scenario.project_ids
                if "project_ids" not in changes or changes["project_ids"] is None
                else changes["project_ids"]
            ),
            intake_item_ids=(
                scenario.intake_item_ids
                if "intake_item_ids" not in changes or changes["intake_item_ids"] is None
                else changes["intake_item_ids"]
            ),
            notes=scenario.notes if changes.get("notes") is None else changes["notes"],
            updated_at=self._utc_now(),
        )
        if "project_ids" in changes and changes["project_ids"] is not None:
            candidate = replace(
                candidate,
                project_ids=self._validate_project_ids(candidate.project_ids),
            )
        if "intake_item_ids" in changes and changes["intake_item_ids"] is not None:
            candidate = replace(
                candidate,
                intake_item_ids=self._validate_intake_ids(candidate.intake_item_ids),
            )
        try:
            self._scenario_repo.update(candidate)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.portfolio_changed.emit(candidate.id)
        return candidate


__all__ = ["PortfolioScenarioCommandMixin"]
