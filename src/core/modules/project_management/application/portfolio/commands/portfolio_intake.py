from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
)
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.shared.events.domain_events import domain_events


class PortfolioIntakeCommandMixin:
    def create_intake_item(
        self,
        *,
        title: str,
        sponsor_name: str,
        summary: str = "",
        requested_budget: float = 0.0,
        requested_capacity_percent: float = 0.0,
        target_start_date=None,
        strategic_score: int = 3,
        value_score: int = 3,
        urgency_score: int = 3,
        risk_score: int = 3,
        scoring_template_id: str | None = None,
        status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED,
    ) -> PortfolioIntakeItem:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio intake")
        organization_id = self._active_portfolio_organization_id(operation_label="create portfolio intake")
        scoring_template = self._resolve_scoring_template(scoring_template_id)
        item = PortfolioIntakeItem.create(
            organization_id=organization_id,
            title=title,
            sponsor_name=sponsor_name,
            summary=summary,
            requested_budget=requested_budget,
            requested_capacity_percent=requested_capacity_percent,
            target_start_date=target_start_date,
            strategic_score=strategic_score,
            value_score=value_score,
            urgency_score=urgency_score,
            risk_score=risk_score,
            scoring_template_id=scoring_template.id,
            scoring_template_name=scoring_template.name,
            strategic_weight=scoring_template.strategic_weight,
            value_weight=scoring_template.value_weight,
            urgency_weight=scoring_template.urgency_weight,
            risk_weight=scoring_template.risk_weight,
            status=status,
        )
        self._intake_repo.add(item)
        self._session.commit()
        domain_events.portfolio_changed.emit(item.id)
        return item

    def update_intake_item(self, item_id: str, **changes) -> PortfolioIntakeItem:
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio intake")
        self._active_portfolio_organization_id(operation_label="update portfolio intake")
        item = self._intake_repo.get(item_id)
        if item is None:
            raise NotFoundError("Portfolio intake item not found.", code="PORTFOLIO_INTAKE_NOT_FOUND")
        candidate = replace(
            item,
            title=item.title if changes.get("title") is None else changes["title"],
            sponsor_name=item.sponsor_name if changes.get("sponsor_name") is None else changes["sponsor_name"],
            summary=item.summary if changes.get("summary") is None else changes["summary"],
            requested_budget=(
                item.requested_budget
                if changes.get("requested_budget") is None
                else changes["requested_budget"]
            ),
            requested_capacity_percent=(
                item.requested_capacity_percent
                if changes.get("requested_capacity_percent") is None
                else changes["requested_capacity_percent"]
            ),
            target_start_date=(
                item.target_start_date
                if "target_start_date" not in changes
                else changes["target_start_date"]
            ),
            strategic_score=(
                item.strategic_score
                if changes.get("strategic_score") is None
                else changes["strategic_score"]
            ),
            value_score=(
                item.value_score
                if changes.get("value_score") is None
                else changes["value_score"]
            ),
            urgency_score=(
                item.urgency_score
                if changes.get("urgency_score") is None
                else changes["urgency_score"]
            ),
            risk_score=(
                item.risk_score
                if changes.get("risk_score") is None
                else changes["risk_score"]
            ),
            status=item.status if changes.get("status") is None else changes["status"],
            updated_at=self._utc_now(),
        )
        if "scoring_template_id" in changes and changes["scoring_template_id"] is not None:
            scoring_template = self._resolve_scoring_template(changes["scoring_template_id"])
            candidate = self._apply_scoring_template(candidate, scoring_template)
        self._intake_repo.update(candidate)
        self._session.commit()
        domain_events.portfolio_changed.emit(candidate.id)
        return candidate


__all__ = ["PortfolioIntakeCommandMixin"]
