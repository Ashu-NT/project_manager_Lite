from __future__ import annotations

from src.core.platform.access.authorization import filter_project_rows
from src.core.platform.common.exceptions import ValidationError
from core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioScenarioComparison,
    PortfolioScoringTemplate,
)


class PortfolioSupportMixin:
    def _accessible_projects(self):
        projects = self._project_repo.list_all()
        return filter_project_rows(
            projects,
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )

    @staticmethod
    def _require_non_empty(value: str, label: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValidationError(f"{label} is required.")
        return text

    @staticmethod
    def _non_negative(value: float, label: str) -> float:
        amount = float(value or 0.0)
        if amount < 0:
            raise ValidationError(f"{label} cannot be negative.")
        return amount

    @staticmethod
    def _bounded_score(value: int) -> int:
        score = int(value or 0)
        if score < 1 or score > 5:
            raise ValidationError("Scores must be between 1 and 5.")
        return score

    @staticmethod
    def _as_intake_status(value: PortfolioIntakeStatus | str) -> PortfolioIntakeStatus:
        if isinstance(value, PortfolioIntakeStatus):
            return value
        return PortfolioIntakeStatus(str(value or PortfolioIntakeStatus.PROPOSED.value))

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
        total_budget: float,
        budget_limit: float | None,
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

    def _ensure_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        templates = self._scoring_template_repo.list_all()
        if templates:
            if not any(template.is_active for template in templates):
                templates[0].is_active = True
                templates[0].updated_at = self._utc_now()
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
                from src.core.platform.common.exceptions import NotFoundError

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
            template.updated_at = self._utc_now()
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
        known_ids = {item.id for item in self._intake_repo.list_all()}
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
