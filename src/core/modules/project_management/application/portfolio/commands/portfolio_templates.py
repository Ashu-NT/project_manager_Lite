from __future__ import annotations

from dataclasses import replace

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.domain.portfolio import PortfolioScoringTemplate
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.audit import record_audit_entry
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioScoringTemplateChangeType,
    PortfolioScoringTemplateChanged,
)


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
        try:
            with self._require_uow_factory().create(context=self._new_context()) as uow:
                events: list = []
                templates = uow.scoring_templates.list()
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
                    self._deactivate_other_templates(uow=uow, events=events)
                uow.scoring_templates.add(template)
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="portfolio_scoring_template",
                    entity_id=template.id,
                    module="project_management",
                    severity="low",
                    metadata={"action": "portfolio.scoring_template.create", "name": template.name},
                    commit=False,
                    fail_closed=True,
                )
                events.append(
                    self._scoring_template_event(template, PortfolioScoringTemplateChangeType.CREATED)
                )
                for event in events:
                    uow.record_event(event)
                uow.commit()
        except IntegrityError as exc:
            raise ConcurrencyError(
                "Another scoring template activation conflicted with this request. Please retry.",
                code="PORTFOLIO_TEMPLATE_ACTIVATION_CONFLICT",
            ) from exc
        return template

    def activate_scoring_template(self, template_id: str) -> PortfolioScoringTemplate:
        require_permission(self._user_session, "portfolio.manage", operation_label="activate scoring template")
        self._active_portfolio_organization_id(operation_label="activate scoring template")
        template = self._scoring_template_repo.get(template_id)
        if template is None:
            raise NotFoundError(
                "Portfolio scoring template not found.",
                code="PORTFOLIO_TEMPLATE_NOT_FOUND",
            )
        if template.is_active:
            return template
        try:
            with self._require_uow_factory().create(context=self._new_context()) as uow:
                events: list = []
                self._deactivate_other_templates(uow=uow, events=events)
                candidate = replace(template, is_active=True, updated_at=self._utc_now())
                uow.scoring_templates.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="portfolio_scoring_template",
                    entity_id=candidate.id,
                    module="project_management",
                    severity="low",
                    metadata={"action": "portfolio.scoring_template.activate", "name": candidate.name},
                    commit=False,
                    fail_closed=True,
                )
                events.append(
                    self._scoring_template_event(candidate, PortfolioScoringTemplateChangeType.ACTIVATED)
                )
                for event in events:
                    uow.record_event(event)
                uow.commit()
        except IntegrityError as exc:
            raise ConcurrencyError(
                "Another scoring template activation conflicted with this request. Please retry.",
                code="PORTFOLIO_TEMPLATE_ACTIVATION_CONFLICT",
            ) from exc
        return candidate


__all__ = ["PortfolioTemplateCommandMixin"]
