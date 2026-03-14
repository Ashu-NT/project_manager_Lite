from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.common.interfaces import (
    AuditLogRepository,
    PortfolioIntakeRepository,
    PortfolioScoringTemplateRepository,
    PortfolioScenarioRepository,
    ProjectRepository,
    ResourceRepository,
)
from core.platform.common.models import (
    PortfolioExecutiveRow,
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioRecentAction,
    PortfolioScoringTemplate,
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
)
from core.platform.access.authorization import filter_project_rows
from core.platform.auth.authorization import require_permission
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.reporting import ReportingService


class PortfolioService(ProjectManagementModuleGuardMixin):
    DEFAULT_TEMPLATE_NAME = "Balanced PMO"
    DEFAULT_TEMPLATE_SUMMARY = "Balanced template for strategic fit, value, urgency, and delivery risk."

    def __init__(
        self,
        *,
        session: Session,
        intake_repo: PortfolioIntakeRepository,
        scoring_template_repo: PortfolioScoringTemplateRepository,
        scenario_repo: PortfolioScenarioRepository,
        audit_repo: AuditLogRepository,
        project_repo: ProjectRepository,
        resource_repo: ResourceRepository,
        reporting_service: ReportingService,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._intake_repo = intake_repo
        self._scoring_template_repo = scoring_template_repo
        self._scenario_repo = scenario_repo
        self._audit_repo = audit_repo
        self._project_repo = project_repo
        self._resource_repo = resource_repo
        self._reporting = reporting_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

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
        item.updated_at = datetime.now(timezone.utc)
        self._intake_repo.update(item)
        self._session.commit()
        domain_events.portfolio_changed.emit(item.id)
        return item

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

    def list_portfolio_heatmap(self) -> list[PortfolioExecutiveRow]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio executive heatmap")
        rows: list[PortfolioExecutiveRow] = []
        for project in self._accessible_projects():
            try:
                kpi = self._reporting.get_project_kpis(project.id)
                resource_rows = self._reporting.get_resource_load_summary(project.id)
                peak_utilization = max(
                    (
                        float(getattr(row, "utilization_percent", 0.0) or 0.0)
                        for row in resource_rows
                    ),
                    default=0.0,
                )
                pressure_score = 0
                if int(kpi.late_tasks or 0) > 0:
                    pressure_score += 2
                if int(kpi.critical_tasks or 0) > 0:
                    pressure_score += 1
                if peak_utilization > 100.0:
                    pressure_score += 2
                elif peak_utilization >= 85.0:
                    pressure_score += 1
                if float(kpi.cost_variance or 0.0) > 0.0:
                    pressure_score += 1
                pressure_label = self._pressure_label(pressure_score)
                late_tasks = int(kpi.late_tasks or 0)
                critical_tasks = int(kpi.critical_tasks or 0)
                cost_variance = float(kpi.cost_variance or 0.0)
            except (BusinessRuleError, ValidationError):
                peak_utilization = 0.0
                pressure_score = 0
                pressure_label = "Needs Schedule"
                late_tasks = 0
                critical_tasks = 0
                cost_variance = 0.0
            rows.append(
                PortfolioExecutiveRow(
                    project_id=project.id,
                    project_name=project.name,
                    project_status=getattr(project.status, "value", str(project.status)),
                    late_tasks=late_tasks,
                    critical_tasks=critical_tasks,
                    peak_utilization_percent=peak_utilization,
                    cost_variance=cost_variance,
                    pressure_score=pressure_score,
                    pressure_label=pressure_label,
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                -row.pressure_score,
                -row.late_tasks,
                -row.peak_utilization_percent,
                row.project_name.lower(),
            ),
        )

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        require_permission(self._user_session, "portfolio.read", operation_label="view recent PM actions")
        accessible_projects = {project.id: project.name for project in self._accessible_projects()}
        pm_prefixes = (
            "project.",
            "task.",
            "baseline.",
            "approval.",
            "timesheet_period.",
            "project_membership.",
            "portfolio.",
        )
        recent_rows = self._audit_repo.list_recent(limit=max(limit * 8, 120))
        actions: list[PortfolioRecentAction] = []
        for row in recent_rows:
            if row.project_id and row.project_id not in accessible_projects:
                continue
            if not str(row.action or "").startswith(pm_prefixes):
                continue
            actions.append(
                PortfolioRecentAction(
                    occurred_at=row.occurred_at,
                    project_name=accessible_projects.get(row.project_id or "", "Platform / Shared"),
                    actor_username=row.actor_username or "system",
                    action_label=self._audit_action_label(row.action),
                    summary=self._audit_summary(row),
                )
            )
            if len(actions) >= limit:
                break
        return actions

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
        intake_by_id = {item.id: item for item in self._intake_repo.list_all()}
        selected_projects, selected_intake = self._scenario_selection(
            scenario,
            accessible_projects=projects,
            intake_by_id=intake_by_id,
        )
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

    def compare_scenarios(
        self,
        base_scenario_id: str,
        candidate_scenario_id: str,
    ) -> PortfolioScenarioComparison:
        require_permission(self._user_session, "portfolio.read", operation_label="compare portfolio scenarios")
        normalized_base = str(base_scenario_id or "").strip()
        normalized_candidate = str(candidate_scenario_id or "").strip()
        if not normalized_base or not normalized_candidate:
            raise ValidationError("Select two scenarios to compare.", code="PORTFOLIO_COMPARISON_REQUIRED")
        if normalized_base == normalized_candidate:
            raise ValidationError(
                "Choose two different scenarios to compare.",
                code="PORTFOLIO_COMPARISON_DUPLICATE",
            )

        base_scenario = self._scenario_repo.get(normalized_base)
        candidate_scenario = self._scenario_repo.get(normalized_candidate)
        if base_scenario is None or candidate_scenario is None:
            raise NotFoundError("Portfolio scenario not found.", code="PORTFOLIO_SCENARIO_NOT_FOUND")

        base_evaluation = self.evaluate_scenario(base_scenario.id)
        candidate_evaluation = self.evaluate_scenario(candidate_scenario.id)

        accessible_projects = {project.id: project for project in self._accessible_projects()}
        intake_by_id = {item.id: item for item in self._intake_repo.list_all()}
        base_projects, base_intake = self._scenario_selection(
            base_scenario,
            accessible_projects=accessible_projects,
            intake_by_id=intake_by_id,
        )
        candidate_projects, candidate_intake = self._scenario_selection(
            candidate_scenario,
            accessible_projects=accessible_projects,
            intake_by_id=intake_by_id,
        )

        base_project_names = {project.name for project in base_projects}
        candidate_project_names = {project.name for project in candidate_projects}
        base_intake_titles = {item.title for item in base_intake}
        candidate_intake_titles = {item.title for item in candidate_intake}

        comparison = PortfolioScenarioComparison(
            base_scenario_id=base_scenario.id,
            base_scenario_name=base_scenario.name,
            candidate_scenario_id=candidate_scenario.id,
            candidate_scenario_name=candidate_scenario.name,
            base_evaluation=base_evaluation,
            candidate_evaluation=candidate_evaluation,
            budget_delta=candidate_evaluation.total_budget - base_evaluation.total_budget,
            capacity_delta_percent=(
                candidate_evaluation.total_capacity_percent - base_evaluation.total_capacity_percent
            ),
            intake_score_delta=candidate_evaluation.intake_composite_score - base_evaluation.intake_composite_score,
            selected_projects_delta=candidate_evaluation.selected_projects - base_evaluation.selected_projects,
            selected_intake_items_delta=(
                candidate_evaluation.selected_intake_items - base_evaluation.selected_intake_items
            ),
            added_project_names=sorted(candidate_project_names - base_project_names),
            removed_project_names=sorted(base_project_names - candidate_project_names),
            added_intake_titles=sorted(candidate_intake_titles - base_intake_titles),
            removed_intake_titles=sorted(base_intake_titles - candidate_intake_titles),
        )
        comparison.summary = self._build_comparison_summary(comparison)
        return comparison

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
    def _scenario_selection(
        scenario: PortfolioScenario,
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
    def _require_non_empty(value: str, label: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValidationError(f"{label} is required.")
        return text

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


__all__ = ["PortfolioService"]
