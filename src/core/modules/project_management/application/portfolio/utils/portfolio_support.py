from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.access.scope_permissions import filter_project_rows
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioScenarioComparison,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioScoringTemplateChangeType,
    PortfolioScoringTemplateChanged,
)
from src.core.shared.audit import record_audit_entry


class PortfolioSupportMixin:
    def _accessible_projects(self):
        self._active_portfolio_organization_id(operation_label="view portfolio projects")
        projects = self._project_repo.list()
        return filter_project_rows(
            projects,
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )

    def _active_portfolio_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            from src.core.platform.common.exceptions import BusinessRuleError
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)

    def _active_portfolio_scope(self, *, operation_label: str):
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            from src.core.platform.common.exceptions import BusinessRuleError
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_scope_ids(operation_label=operation_label)

    @staticmethod
    def _scenario_selection(
        scenario,
        *,
        accessible_projects: dict[str, object],
        intake_by_id: dict[str, PortfolioIntakeItem],
    ) -> tuple[list[object], list[PortfolioIntakeItem]]:
        selected_projects = [
            accessible_projects[project_id]
            for project_id in scenario.project_ids
            if project_id in accessible_projects
        ]
        selected_intake = [
            intake_by_id[item_id]
            for item_id in scenario.intake_item_ids
            if item_id in intake_by_id
        ]
        return selected_projects, selected_intake

    @staticmethod
    def _build_evaluation_summary(
        *,
        over_budget: bool,
        over_capacity: bool,
        total_budget: Decimal,
        budget_limit: Decimal | None,
        total_capacity_percent: float,
        capacity_limit: float,
        selected_projects: int,
        selected_intake: int,
    ) -> str:
        budget_text = (
            f"budget {total_budget:.2f}/{budget_limit:.2f}"
            if budget_limit is not None
            else f"budget {total_budget:.2f}"
        )
        capacity_text = f"capacity {total_capacity_percent:.1f}/{capacity_limit:.1f}%"
        state: list[str] = []
        if over_budget:
            state.append("over budget")
        if over_capacity:
            state.append("over capacity")
        if not state:
            state.append("within limits")
        return (
            f"{selected_projects} project(s) and {selected_intake} intake item(s); "
            f"{budget_text}; {capacity_text}; {', '.join(state)}."
        )

    @staticmethod
    def _build_comparison_summary(comparison: PortfolioScenarioComparison) -> str:
        parts = [
            f"{comparison.candidate_scenario_name} vs {comparison.base_scenario_name}",
            f"budget delta {comparison.budget_delta:+.2f}",
            f"capacity delta {comparison.capacity_delta_percent:+.1f}%",
            f"intake score delta {comparison.intake_score_delta:+d}",
        ]
        if comparison.added_project_names:
            parts.append(f"added projects: {', '.join(comparison.added_project_names)}")
        if comparison.removed_project_names:
            parts.append(f"removed projects: {', '.join(comparison.removed_project_names)}")
        if comparison.added_intake_titles:
            parts.append(f"added intake: {', '.join(comparison.added_intake_titles)}")
        if comparison.removed_intake_titles:
            parts.append(f"removed intake: {', '.join(comparison.removed_intake_titles)}")
        return "; ".join(parts) + "."

    @staticmethod
    def _pressure_label(score: int) -> str:
        if score >= 4:
            return "Hot"
        if score >= 2:
            return "Watch"
        return "Stable"

    @staticmethod
    def _audit_action_label(action: str) -> str:
        action_name = str(action or "").strip()
        if not action_name:
            return "Update"
        return action_name.replace(".", " ").replace("_", " ").title()

    @staticmethod
    def _audit_summary(row) -> str:
        details = dict(getattr(row, "details", {}) or {})
        for key in ("note", "status", "title", "summary", "message"):
            value = str(details.get(key) or "").strip()
            if value:
                return value
        entity_type = str(getattr(row, "entity_type", "") or "record").replace("_", " ")
        return f"{entity_type.title()} updated."

    def _scoring_template_event(
        self, template: PortfolioScoringTemplate, change_type: PortfolioScoringTemplateChangeType
    ) -> PortfolioScoringTemplateChanged:
        scope = self._active_portfolio_scope(operation_label="record scoring template fact")
        return PortfolioScoringTemplateChanged(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            scoring_template_id=template.id,
            change_type=change_type,
            occurred_at=self._utc_now(),
        )

    def _ensure_scoring_templates(
        self, *, uow, events: list
    ) -> list[PortfolioScoringTemplate]:

        templates_repo = uow.scoring_templates
        organization_id = self._active_portfolio_organization_id(operation_label="view scoring templates")
        templates = templates_repo.list()
        if templates:
            if not any(template.is_active for template in templates):
                templates[0].is_active = True
                templates[0].updated_at = self._utc_now()
                templates_repo.update(templates[0])
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="portfolio_scoring_template",
                    entity_id=templates[0].id,
                    module="project_management",
                    organization_id=organization_id,
                    severity="low",
                    metadata={
                        "action": "portfolio.scoring_template.bootstrap_reactivate",
                        "name": templates[0].name,
                    },
                    commit=False,
                    fail_closed=True,
                )
                events.append(
                    self._scoring_template_event(
                        templates[0], PortfolioScoringTemplateChangeType.ACTIVATED
                    )
                )
                templates = templates_repo.list()
            return templates
        default_template = PortfolioScoringTemplate.create(
            organization_id=organization_id,
            name=self.DEFAULT_TEMPLATE_NAME,
            summary=self.DEFAULT_TEMPLATE_SUMMARY,
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
            severity="low",
            metadata={
                "action": "portfolio.scoring_template.bootstrap_create",
                "name": default_template.name,
            },
            commit=False,
            fail_closed=True,
        )
        events.append(
            self._scoring_template_event(default_template, PortfolioScoringTemplateChangeType.CREATED)
        )
        return [default_template]

    def _scoring_templates_with_bootstrap(self) -> list[PortfolioScoringTemplate]:
        templates = self._scoring_template_repo.list()
        if templates and any(template.is_active for template in templates):
            return templates
        try:
            with self._require_uow_factory().create(context=self._new_context()) as uow:
                events: list = []
                templates = self._ensure_scoring_templates(uow=uow, events=events)
                for event in events:
                    uow.record_event(event)
                uow.commit()
        except IntegrityError:
            templates = self._scoring_template_repo.list()
        return templates

    def _active_scoring_template_resolved(self) -> PortfolioScoringTemplate:
        templates = self._scoring_templates_with_bootstrap()
        for template in templates:
            if template.is_active:
                return template
        return templates[0]

    def _active_scoring_template(self, *, uow, events: list) -> PortfolioScoringTemplate:
        templates = self._ensure_scoring_templates(uow=uow, events=events)
        for template in templates:
            if template.is_active:
                return template
        return templates[0]

    def _resolve_scoring_template(
        self, scoring_template_id: str | None, *, uow, events: list
    ) -> PortfolioScoringTemplate:
        normalized_id = str(scoring_template_id or "").strip()
        if normalized_id:
            self._active_portfolio_organization_id(operation_label="view scoring template")
            template = uow.scoring_templates.get(normalized_id)
            if template is None:
                raise NotFoundError(
                    "Portfolio scoring template not found.",
                    code="PORTFOLIO_TEMPLATE_NOT_FOUND",
                )
            return template
        return self._active_scoring_template(uow=uow, events=events)

    @staticmethod
    def _apply_scoring_template(
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

    def _deactivate_other_templates(self, *, uow, events: list) -> None:
        organization_id = self._active_portfolio_organization_id(
            operation_label="deactivate portfolio scoring templates"
        )
        for template in self._ensure_scoring_templates(uow=uow, events=events):
            if not template.is_active:
                continue
            template.is_active = False
            template.updated_at = self._utc_now()
            uow.scoring_templates.update(template)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="portfolio_scoring_template",
                entity_id=template.id,
                module="project_management",
                organization_id=organization_id,
                severity="low",
                metadata={"action": "portfolio.scoring_template.deactivate", "name": template.name},
                commit=False,
                fail_closed=True,
            )
            events.append(
                self._scoring_template_event(template, PortfolioScoringTemplateChangeType.DEACTIVATED)
            )

    def _validate_project_ids(self, project_ids: list[str]) -> list[str]:
        known_ids = {project.id for project in self._accessible_projects()}
        invalid = [project_id for project_id in project_ids if project_id not in known_ids]
        if invalid:
            raise ValidationError(
                f"Scenario contains unknown or inaccessible project ids: {', '.join(invalid)}.",
                code="PORTFOLIO_PROJECT_SCOPE_INVALID",
            )
        return sorted({project_id for project_id in project_ids if project_id})

    def _validate_intake_ids(self, intake_item_ids: list[str]) -> list[str]:
        self._active_portfolio_organization_id(operation_label="validate intake ids")
        known_ids = {item.id for item in self._intake_repo.list()}
        invalid = [item_id for item_id in intake_item_ids if item_id not in known_ids]
        if invalid:
            raise ValidationError(
                f"Scenario contains unknown intake item ids: {', '.join(invalid)}.",
                code="PORTFOLIO_INTAKE_SCOPE_INVALID",
            )
        return sorted({item_id for item_id in intake_item_ids if item_id})

    @staticmethod
    def _utc_now():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)


__all__ = ["PortfolioSupportMixin"]
