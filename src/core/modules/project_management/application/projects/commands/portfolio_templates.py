from __future__ import annotations

from src.core.modules.project_management.domain.portfolio import PortfolioScoringTemplate
from src.core.platform.auth.authorization import require_permission
from src.core.platform.notifications.domain_events import domain_events
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
        templates = self._ensure_scoring_templates()
        normalized_name = self._require_non_empty(name, "Template name")
        if any(template.name.casefold() == normalized_name.casefold() for template in templates):
            raise ValidationError(
                "A scoring template with that name already exists.",
                code="PORTFOLIO_TEMPLATE_DUPLICATE",
            )
        template = PortfolioScoringTemplate.create(
            name=normalized_name,
            summary=(summary or "").strip(),
            strategic_weight=self._template_weight(strategic_weight, "Strategic weight"),
            value_weight=self._template_weight(value_weight, "Value weight"),
            urgency_weight=self._template_weight(urgency_weight, "Urgency weight"),
            risk_weight=self._template_weight(risk_weight, "Risk weight"),
            is_active=bool(activate),
        )
        self._validate_template_mix(template)
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
        template.is_active = True
        template.updated_at = self._utc_now()
        self._scoring_template_repo.update(template)
        self._session.commit()
        domain_events.portfolio_changed.emit(template.id)
        return template


__all__ = ["PortfolioTemplateCommandMixin"]
