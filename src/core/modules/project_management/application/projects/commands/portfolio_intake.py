from __future__ import annotations

from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
)
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.notifications.domain_events import domain_events


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
        scoring_template = self._resolve_scoring_template(scoring_template_id)
        item = PortfolioIntakeItem.create(
            title=self._require_non_empty(title, "Title"),
            sponsor_name=self._require_non_empty(sponsor_name, "Sponsor"),
            summary=summary,
            requested_budget=self._non_negative(requested_budget, "Requested budget"),
            requested_capacity_percent=self._non_negative(
                requested_capacity_percent,
                "Requested capacity",
            ),
            target_start_date=target_start_date,
            strategic_score=self._bounded_score(strategic_score),
            value_score=self._bounded_score(value_score),
            urgency_score=self._bounded_score(urgency_score),
            risk_score=self._bounded_score(risk_score),
            scoring_template_id=scoring_template.id,
            scoring_template_name=scoring_template.name,
            strategic_weight=scoring_template.strategic_weight,
            value_weight=scoring_template.value_weight,
            urgency_weight=scoring_template.urgency_weight,
            risk_weight=scoring_template.risk_weight,
            status=self._as_intake_status(status),
        )
        self._intake_repo.add(item)
        self._session.commit()
        domain_events.portfolio_changed.emit(item.id)
        return item

    def update_intake_item(self, item_id: str, **changes) -> PortfolioIntakeItem:
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio intake")
        item = self._intake_repo.get(item_id)
        if item is None:
            raise NotFoundError("Portfolio intake item not found.", code="PORTFOLIO_INTAKE_NOT_FOUND")
        if "title" in changes and changes["title"] is not None:
            item.title = self._require_non_empty(changes["title"], "Title")
        if "sponsor_name" in changes and changes["sponsor_name"] is not None:
            item.sponsor_name = self._require_non_empty(changes["sponsor_name"], "Sponsor")
        if "summary" in changes and changes["summary"] is not None:
            item.summary = (changes["summary"] or "").strip()
        if "requested_budget" in changes and changes["requested_budget"] is not None:
            item.requested_budget = self._non_negative(changes["requested_budget"], "Requested budget")
        if "requested_capacity_percent" in changes and changes["requested_capacity_percent"] is not None:
            item.requested_capacity_percent = self._non_negative(
                changes["requested_capacity_percent"],
                "Requested capacity",
            )
        if "target_start_date" in changes:
            item.target_start_date = changes["target_start_date"]
        if "strategic_score" in changes and changes["strategic_score"] is not None:
            item.strategic_score = self._bounded_score(changes["strategic_score"])
        if "value_score" in changes and changes["value_score"] is not None:
            item.value_score = self._bounded_score(changes["value_score"])
        if "urgency_score" in changes and changes["urgency_score"] is not None:
            item.urgency_score = self._bounded_score(changes["urgency_score"])
        if "risk_score" in changes and changes["risk_score"] is not None:
            item.risk_score = self._bounded_score(changes["risk_score"])
        if "scoring_template_id" in changes and changes["scoring_template_id"] is not None:
            scoring_template = self._resolve_scoring_template(changes["scoring_template_id"])
            self._apply_scoring_template(item, scoring_template)
        if "status" in changes and changes["status"] is not None:
            item.status = self._as_intake_status(changes["status"])
        item.updated_at = self._utc_now()
        self._intake_repo.update(item)
        self._session.commit()
        domain_events.portfolio_changed.emit(item.id)
        return item


__all__ = ["PortfolioIntakeCommandMixin"]
