from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.domain.portfolio import PortfolioScoringTemplate
from src.core.platform.auth.authorization import require_permission
from src.core.shared.events.domain_events import domain_events
from src.core.platform.common.exceptions import ValidationError


class PortfolioTemplateCommandMixin:
    def create_scoring_template(
        self,
        *,
        name: str,
        summary: str = "",
        strategic_weight: int = 3,
        value_weight: int = 2,
        urgency_weight: int = 2,
        risk_weight: int = 1,
        activate: bool = False,
    ) -> PortfolioScoringTemplate:
        require_permission(self._user_session, "portfolio.manage", operation_label="create scoring template")
        organization_id = self._active_portfolio_organization_id(operation_label="create scoring template")
        templates = self._ensure_scoring_templates()
        template = PortfolioScoringTemplate.create(
            organization_id=organization_id,
            name=name,
            summary=summary,
            strategic_weight=strategic_weight,
            value_weight=value_weight,
            urgency_weight=urgency_weight,
            risk_weight=risk_weight,
            is_active=bool(activate),
        )
        if any(existing.name.casefold() == template.name.casefold() for existing in templates):
            raise ValidationError(
                "A scoring template with that name already exists.",
                code="PORTFOLIO_TEMPLATE_DUPLICATE",
            )
        if activate:
            self._deactivate_other_templates()
        self._scoring_template_repo.add(template)
        self._session.commit()
        domain_events.portfolio_changed.emit(template.id)
        return template

    def activate_scoring_template(self, template_id: str) -> PortfolioScoringTemplate:
        require_permission(self._user_session, "portfolio.manage", operation_label="activate scoring template")
        template = self._resolve_scoring_template(template_id)
        if template.is_active:
            return template
        self._deactivate_other_templates()
        candidate = replace(template, is_active=True, updated_at=self._utc_now())
        self._scoring_template_repo.update(candidate)
        self._session.commit()
        domain_events.portfolio_changed.emit(candidate.id)
        return candidate


__all__ = ["PortfolioTemplateCommandMixin"]
