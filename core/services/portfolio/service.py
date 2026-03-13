from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.events.domain_events import domain_events
from core.exceptions import NotFoundError, ValidationError
from core.interfaces import (
    PortfolioIntakeRepository,
    PortfolioScenarioRepository,
    ProjectRepository,
    ResourceRepository,
)
from core.models import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioScenario,
    PortfolioScenarioEvaluation,
)
from core.services.access.authorization import filter_project_rows
from core.services.auth.authorization import require_permission
from core.services.reporting import ReportingService


class PortfolioService:
    def __init__(
        self,
        *,
        session: Session,
        intake_repo: PortfolioIntakeRepository,
        scenario_repo: PortfolioScenarioRepository,
        project_repo: ProjectRepository,
        resource_repo: ResourceRepository,
        reporting_service: ReportingService,
        user_session=None,
    ) -> None:
        self._session = session
        self._intake_repo = intake_repo
        self._scenario_repo = scenario_repo
        self._project_repo = project_repo
        self._resource_repo = resource_repo
        self._reporting = reporting_service
        self._user_session = user_session

    def list_intake_items(
        self,
        *,
        status: PortfolioIntakeStatus | None = None,
    ) -> list[PortfolioIntakeItem]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio intake")
        rows = self._intake_repo.list_all()
        if status is None:
            return rows
        return [row for row in rows if row.status == status]

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
        status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED,
    ) -> PortfolioIntakeItem:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio intake")
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
            status=status,
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
        if "status" in changes and changes["status"] is not None:
            item.status = PortfolioIntakeStatus(changes["status"])
        item.updated_at = datetime.now(timezone.utc)
        self._intake_repo.update(item)
        self._session.commit()
        domain_events.portfolio_changed.emit(item.id)
        return item

    def list_scenarios(self) -> list[PortfolioScenario]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio scenarios")
        return self._scenario_repo.list_all()

    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: float | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio scenario")
        scenario = PortfolioScenario.create(
            name=self._require_non_empty(name, "Scenario name"),
            budget_limit=(None if budget_limit is None else self._non_negative(budget_limit, "Budget limit")),
            capacity_limit_percent=(
                None
                if capacity_limit_percent is None
                else self._non_negative(capacity_limit_percent, "Capacity limit")
            ),
            project_ids=self._validate_project_ids(project_ids or []),
            intake_item_ids=self._validate_intake_ids(intake_item_ids or []),
            notes=notes,
        )
        self._scenario_repo.add(scenario)
        self._session.commit()
        domain_events.portfolio_changed.emit(scenario.id)
        return scenario

    def update_scenario(self, scenario_id: str, **changes) -> PortfolioScenario:
        require_permission(self._user_session, "portfolio.manage", operation_label="update portfolio scenario")
        scenario = self._scenario_repo.get(scenario_id)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        if "name" in changes and changes["name"] is not None:
            scenario.name = self._require_non_empty(changes["name"], "Scenario name")
        if "budget_limit" in changes:
            scenario.budget_limit = (
                None
                if changes["budget_limit"] is None
                else self._non_negative(changes["budget_limit"], "Budget limit")
            )
        if "capacity_limit_percent" in changes:
            scenario.capacity_limit_percent = (
                None
                if changes["capacity_limit_percent"] is None
                else self._non_negative(changes["capacity_limit_percent"], "Capacity limit")
            )
        if "project_ids" in changes and changes["project_ids"] is not None:
            scenario.project_ids = self._validate_project_ids(list(changes["project_ids"]))
        if "intake_item_ids" in changes and changes["intake_item_ids"] is not None:
            scenario.intake_item_ids = self._validate_intake_ids(list(changes["intake_item_ids"]))
        if "notes" in changes and changes["notes"] is not None:
            scenario.notes = (changes["notes"] or "").strip()
        scenario.updated_at = datetime.now(timezone.utc)
        self._scenario_repo.update(scenario)
        self._session.commit()
        domain_events.portfolio_changed.emit(scenario.id)
        return scenario

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        require_permission(self._user_session, "portfolio.read", operation_label="evaluate portfolio scenario")
        scenario = self._scenario_repo.get(scenario_id)
        if scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")
        projects = {project.id: project for project in self._accessible_projects()}
        selected_projects = [projects[project_id] for project_id in scenario.project_ids if project_id in projects]
        intake_by_id = {item.id: item for item in self._intake_repo.list_all()}
        selected_intake = [intake_by_id[item_id] for item_id in scenario.intake_item_ids if item_id in intake_by_id]
        total_budget = sum(float(getattr(project, "planned_budget", 0.0) or 0.0) for project in selected_projects)
        total_budget += sum(float(item.requested_budget or 0.0) for item in selected_intake)

        total_capacity_percent = sum(
            sum(float(row.total_allocation_percent or 0.0) for row in self._reporting.get_resource_load_summary(project.id))
            for project in selected_projects
        )
        total_capacity_percent += sum(
            float(item.requested_capacity_percent or 0.0) for item in selected_intake
        )

        available_capacity_percent = sum(
            float(getattr(resource, "capacity_percent", 0.0) or 0.0)
            for resource in self._resource_repo.list_all()
            if bool(getattr(resource, "is_active", True))
        )
        capacity_limit = (
            scenario.capacity_limit_percent
            if scenario.capacity_limit_percent is not None
            else available_capacity_percent
        )
        over_budget = scenario.budget_limit is not None and total_budget > float(scenario.budget_limit)
        over_capacity = total_capacity_percent > float(capacity_limit or 0.0)
        intake_score = sum(int(item.composite_score or 0) for item in selected_intake)
        summary = self._build_evaluation_summary(
            over_budget=over_budget,
            over_capacity=over_capacity,
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity_percent,
            capacity_limit=float(capacity_limit or 0.0),
            selected_projects=len(selected_projects),
            selected_intake=len(selected_intake),
        )
        return PortfolioScenarioEvaluation(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            selected_projects=len(selected_projects),
            selected_intake_items=len(selected_intake),
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity_percent,
            capacity_limit_percent=capacity_limit,
            available_capacity_percent=available_capacity_percent,
            intake_composite_score=intake_score,
            over_budget=over_budget,
            over_capacity=over_capacity,
            summary=summary,
        )

    def _accessible_projects(self):
        projects = self._project_repo.list_all()
        return filter_project_rows(
            projects,
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
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


__all__ = ["PortfolioService"]
