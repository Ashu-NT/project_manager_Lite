"""Shared portfolio scope + scoring-template policy.

One explicit collaborator injected into every portfolio handler that needs
tenant/org scope, accessible-project filtering, scenario id validation, or
scoring-template resolution/bootstrap. Scoring-template bootstrap lives here
exactly once so intake, template and query handlers never duplicate it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.access.scope_permissions import (
    filter_project_rows,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioScoringTemplateChanged,
    PortfolioScoringTemplateChangeType,
)
from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioIntakeRepository,
    PortfolioScoringTemplateRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.uow.portfolio.portfolio_unit_of_work import (
    PortfolioUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioScoringTemplate,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext

DEFAULT_TEMPLATE_NAME = "Balanced PMO"
DEFAULT_TEMPLATE_SUMMARY = "Balanced template for strategic fit, value, urgency, and delivery risk."


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_portfolio_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class PortfolioPolicy:
    def __init__(
        self,
        *,
        tenant_context_service,
        project_repo: ProjectRepository,
        intake_repo: PortfolioIntakeRepository,
        scoring_template_repo: PortfolioScoringTemplateRepository,
        uow_factory: PortfolioUnitOfWorkFactory,
        user_session=None,
    ) -> None:
        if tenant_context_service is None:
            raise BusinessRuleError(
                "Portfolio handlers require TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        self._tenant_context_service = tenant_context_service
        self._project_repo = project_repo
        self._intake_repo = intake_repo
        self._scoring_template_repo = scoring_template_repo
        self._uow_factory = uow_factory
        self._user_session = user_session

    # -- scope -------------------------------------------------------------

    def organization_id(self, *, operation_label: str) -> str:
        return self._tenant_context_service.require_active_organization_id(
            operation_label=operation_label
        )

    def scope(self, *, operation_label: str):
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def accessible_projects(self) -> list:
        self.organization_id(operation_label="view portfolio projects")
        return filter_project_rows(
            self._project_repo.list(),
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )

    def validate_project_ids(self, project_ids: list[str]) -> list[str]:
        known_ids = {project.id for project in self.accessible_projects()}
        invalid = [project_id for project_id in project_ids if project_id not in known_ids]
        if invalid:
            raise ValidationError(
                f"Scenario contains unknown or inaccessible project ids: {', '.join(invalid)}.",
                code="PORTFOLIO_PROJECT_SCOPE_INVALID",
            )
        return sorted({project_id for project_id in project_ids if project_id})

    def validate_intake_ids(self, intake_item_ids: list[str]) -> list[str]:
        self.organization_id(operation_label="validate intake ids")
        known_ids = {item.id for item in self._intake_repo.list()}
        invalid = [item_id for item_id in intake_item_ids if item_id not in known_ids]
        if invalid:
            raise ValidationError(
                f"Scenario contains unknown intake item ids: {', '.join(invalid)}.",
                code="PORTFOLIO_INTAKE_SCOPE_INVALID",
            )
        return sorted({item_id for item_id in intake_item_ids if item_id})

    # -- scoring templates -------------------------------------------------

    def scoring_template_event(
        self, template: PortfolioScoringTemplate, change_type: PortfolioScoringTemplateChangeType
    ) -> PortfolioScoringTemplateChanged:
        scope = self.scope(operation_label="record scoring template fact")
        return PortfolioScoringTemplateChanged(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            scoring_template_id=template.id,
            change_type=change_type,
            occurred_at=utc_now(),
        )

    def ensure_scoring_templates(self, *, uow, events: list) -> list[PortfolioScoringTemplate]:
        templates_repo = uow.scoring_templates
        organization_id = self.organization_id(operation_label="view scoring templates")
        templates = templates_repo.list()
        if templates:
            if not any(template.is_active for template in templates):
                templates[0].is_active = True
                templates[0].updated_at = utc_now()
                templates_repo.update(templates[0])
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="portfolio_scoring_template",
                    entity_id=templates[0].id,
                    module="project_management",
                    organization_id=organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    metadata={"action": "portfolio.scoring_template.bootstrap_reactivate"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="portfolio.scoring_template.bootstrap_reactivate",
                    entity_type="portfolio_scoring_template",
                    entity_id=templates[0].id,
                    module="project_management",
                    organization_id=organization_id,
                    details={"name": templates[0].name},
                    commit=False,
                )
                events.append(
                    self.scoring_template_event(
                        templates[0], PortfolioScoringTemplateChangeType.ACTIVATED
                    )
                )
                templates = templates_repo.list()
            return templates
        default_template = PortfolioScoringTemplate.create(
            organization_id=organization_id,
            name=DEFAULT_TEMPLATE_NAME,
            summary=DEFAULT_TEMPLATE_SUMMARY,
            strategic_weight=3,
            value_weight=2,
            urgency_weight=2,
            risk_weight=1,
            is_active=True,
        )
        templates_repo.add(default_template)
        record_audit_entry(
            uow,
            operation="create",
            entity_type="portfolio_scoring_template",
            entity_id=default_template.id,
            module="project_management",
            organization_id=organization_id,
            category="MASTER_DATA",
            severity="low",
            after_data={"name": default_template.name},
            metadata={"action": "portfolio.scoring_template.bootstrap_create"},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action="portfolio.scoring_template.bootstrap_create",
            entity_type="portfolio_scoring_template",
            entity_id=default_template.id,
            module="project_management",
            organization_id=organization_id,
            details={"name": default_template.name},
            commit=False,
        )
        events.append(
            self.scoring_template_event(default_template, PortfolioScoringTemplateChangeType.CREATED)
        )
        return [default_template]

    def scoring_templates_with_bootstrap(self) -> list[PortfolioScoringTemplate]:
        templates = self._scoring_template_repo.list()
        if templates and any(template.is_active for template in templates):
            return templates
        try:
            with self._uow_factory.create(context=new_portfolio_context()) as uow:
                events: list = []
                templates = self.ensure_scoring_templates(uow=uow, events=events)
                for event in events:
                    uow.record_event(event)
                uow.commit()
        except IntegrityError:
            templates = self._scoring_template_repo.list()
        return templates

    def active_scoring_template_resolved(self) -> PortfolioScoringTemplate:
        templates = self.scoring_templates_with_bootstrap()
        for template in templates:
            if template.is_active:
                return template
        return templates[0]

    def active_scoring_template(self, *, uow, events: list) -> PortfolioScoringTemplate:
        templates = self.ensure_scoring_templates(uow=uow, events=events)
        for template in templates:
            if template.is_active:
                return template
        return templates[0]

    def resolve_scoring_template(
        self, scoring_template_id: str | None, *, uow, events: list
    ) -> PortfolioScoringTemplate:
        normalized_id = str(scoring_template_id or "").strip()
        if normalized_id:
            self.organization_id(operation_label="view scoring template")
            template = uow.scoring_templates.get(normalized_id)
            if template is None:
                raise NotFoundError(
                    "Portfolio scoring template not found.",
                    code="PORTFOLIO_TEMPLATE_NOT_FOUND",
                )
            return template
        return self.active_scoring_template(uow=uow, events=events)

    @staticmethod
    def apply_scoring_template(
        item: PortfolioIntakeItem,
        template: PortfolioScoringTemplate,
    ) -> PortfolioIntakeItem:
        return replace(
            item,
            scoring_template_id=template.id,
            scoring_template_name=template.name,
            strategic_weight=template.strategic_weight,
            value_weight=template.value_weight,
            urgency_weight=template.urgency_weight,
            risk_weight=template.risk_weight,
        )

    def deactivate_other_templates(self, *, uow, events: list) -> None:
        organization_id = self.organization_id(
            operation_label="deactivate portfolio scoring templates"
        )
        for template in self.ensure_scoring_templates(uow=uow, events=events):
            if not template.is_active:
                continue
            template.is_active = False
            template.updated_at = utc_now()
            uow.scoring_templates.update(template)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="portfolio_scoring_template",
                entity_id=template.id,
                module="project_management",
                organization_id=organization_id,
                category="MASTER_DATA",
                severity="low",
                metadata={"action": "portfolio.scoring_template.deactivate"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="portfolio.scoring_template.deactivate",
                entity_type="portfolio_scoring_template",
                entity_id=template.id,
                module="project_management",
                organization_id=organization_id,
                details={"name": template.name},
                commit=False,
            )
            events.append(
                self.scoring_template_event(template, PortfolioScoringTemplateChangeType.DEACTIVATED)
            )


__all__ = [
    "DEFAULT_TEMPLATE_NAME",
    "DEFAULT_TEMPLATE_SUMMARY",
    "PortfolioPolicy",
    "new_portfolio_context",
    "utc_now",
]
