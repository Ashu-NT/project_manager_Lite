from __future__ import annotations

from core.platform.access.authorization import filter_project_rows
from core.platform.common.exceptions import ValidationError
from core.platform.common.models import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioScenarioComparison,
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


__all__ = ["PortfolioSupportMixin"]
