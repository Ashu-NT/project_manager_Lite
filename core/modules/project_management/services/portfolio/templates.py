from __future__ import annotations

from datetime import datetime, timezone

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioScoringTemplate,
)
from src.core.platform.auth.authorization import require_permission


class PortfolioTemplateMixin:
    def list_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        require_permission(self._user_session, "portfolio.read", operation_label="view scoring templates")
        return self._ensure_scoring_templates()

    def get_active_scoring_template(self) -> PortfolioScoringTemplate:
        require_permission(self._user_session, "portfolio.read", operation_label="view active scoring template")
        return self._active_scoring_template()

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
        template.updated_at = datetime.now(timezone.utc)
        self._scoring_template_repo.update(template)
        self._session.commit()
        domain_events.portfolio_changed.emit(template.id)
        return template

    def _ensure_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        templates = self._scoring_template_repo.list_all()
        if templates:
            if not any(template.is_active for template in templates):
                templates[0].is_active = True
                templates[0].updated_at = datetime.now(timezone.utc)
                self._scoring_template_repo.update(templates[0])
                self._session.commit()
                templates = self._scoring_template_repo.list_all()
            return templates
        default_template = PortfolioScoringTemplate.create(
            name=self.DEFAULT_TEMPLATE_NAME,
            summary=self.DEFAULT_TEMPLATE_SUMMARY,
            strategic_weight=3,
            value_weight=2,
            urgency_weight=2,
            risk_weight=1,
            is_active=True,
        )
        self._scoring_template_repo.add(default_template)
        self._session.commit()
        return [default_template]

    def _active_scoring_template(self) -> PortfolioScoringTemplate:
        templates = self._ensure_scoring_templates()
        for template in templates:
            if template.is_active:
                return template
        return templates[0]

    def _resolve_scoring_template(self, template_id: str | None) -> PortfolioScoringTemplate:
        normalized_id = str(template_id or "").strip()
        if normalized_id:
            template = self._scoring_template_repo.get(normalized_id)
            if template is None:
                raise NotFoundError(
                    "Portfolio scoring template not found.",
                    code="PORTFOLIO_TEMPLATE_NOT_FOUND",
                )
            return template
        return self._active_scoring_template()

    @staticmethod
    def _apply_scoring_template(
        item: PortfolioIntakeItem,
        template: PortfolioScoringTemplate,
    ) -> None:
        item.scoring_template_id = template.id
        item.scoring_template_name = template.name
        item.strategic_weight = template.strategic_weight
        item.value_weight = template.value_weight
        item.urgency_weight = template.urgency_weight
        item.risk_weight = template.risk_weight

    def _deactivate_other_templates(self) -> None:
        for template in self._ensure_scoring_templates():
            if not template.is_active:
                continue
            template.is_active = False
            template.updated_at = datetime.now(timezone.utc)
            self._scoring_template_repo.update(template)

    @staticmethod
    def _template_weight(value: int, label: str) -> int:
        weight = int(value or 0)
        if weight < 0 or weight > 9:
            raise ValidationError(f"{label} must be between 0 and 9.")
        return weight

    @staticmethod
    def _validate_template_mix(template: PortfolioScoringTemplate) -> None:
        if (
            int(template.strategic_weight or 0)
            + int(template.value_weight or 0)
            + int(template.urgency_weight or 0)
        ) <= 0:
            raise ValidationError(
                "At least one positive delivery weight is required.",
                code="PORTFOLIO_TEMPLATE_EMPTY",
            )


__all__ = ["PortfolioTemplateMixin"]
