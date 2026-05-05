from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.modules.project_management.application.projects import (
    PortfolioService,
    ProjectService,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus


@dataclass(frozen=True)
class PortfolioOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class PortfolioProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class PortfolioTemplateDesktopDto:
    id: str
    name: str
    summary: str
    weight_summary: str
    is_active: bool
    strategic_weight: int
    value_weight: int
    urgency_weight: int
    risk_weight: int


@dataclass(frozen=True)
class PortfolioIntakeDesktopDto:
    id: str
    title: str
    sponsor_name: str
    summary: str
    requested_budget: float
    requested_budget_label: str
    requested_capacity_percent: float
    requested_capacity_label: str
    target_start_date: date | None
    target_start_date_label: str
    status: str
    status_label: str
    scoring_template_id: str
    scoring_template_name: str
    composite_score: int
    version: int


@dataclass(frozen=True)
class PortfolioScenarioDesktopDto:
    id: str
    name: str
    budget_limit: float | None
    budget_limit_label: str
    capacity_limit_percent: float | None
    capacity_limit_label: str
    project_ids: tuple[str, ...]
    intake_item_ids: tuple[str, ...]
    notes: str
    created_at_label: str


@dataclass(frozen=True)
class PortfolioScenarioEvaluationDesktopDto:
    scenario_id: str
    scenario_name: str
    summary: str
    selected_projects_label: str
    selected_intake_items_label: str
    total_budget_label: str
    budget_limit_label: str
    total_capacity_label: str
    capacity_limit_label: str
    available_capacity_label: str
    intake_score_label: str
    status_label: str


@dataclass(frozen=True)
class PortfolioScenarioComparisonDesktopDto:
    base_scenario_id: str
    base_scenario_name: str
    candidate_scenario_id: str
    candidate_scenario_name: str
    summary: str
    budget_delta_label: str
    capacity_delta_label: str
    intake_score_delta_label: str
    selected_projects_delta_label: str
    selected_intake_items_delta_label: str
    added_project_names: tuple[str, ...]
    removed_project_names: tuple[str, ...]
    added_intake_titles: tuple[str, ...]
    removed_intake_titles: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioHeatmapDesktopDto:
    project_id: str
    project_name: str
    project_status_label: str
    late_tasks: int
    critical_tasks: int
    peak_utilization_percent: float
    peak_utilization_label: str
    cost_variance: float
    cost_variance_label: str
    pressure_label: str


@dataclass(frozen=True)
class PortfolioDependencyDesktopDto:
    dependency_id: str
    predecessor_project_id: str
    predecessor_project_name: str
    predecessor_project_status_label: str
    successor_project_id: str
    successor_project_name: str
    successor_project_status_label: str
    dependency_type: str
    dependency_type_label: str
    summary: str
    pressure_label: str
    created_at_label: str


@dataclass(frozen=True)
class PortfolioRecentActionDesktopDto:
    occurred_at_label: str
    project_name: str
    actor_username: str
    action_label: str
    summary: str


@dataclass(frozen=True)
class PortfolioTemplateCreateCommand:
    name: str
    summary: str = ""
    strategic_weight: int = 3
    value_weight: int = 2
    urgency_weight: int = 2
    risk_weight: int = 1
    activate: bool = False


@dataclass(frozen=True)
class PortfolioIntakeCreateCommand:
    title: str
    sponsor_name: str
    summary: str = ""
    requested_budget: float = 0.0
    requested_capacity_percent: float = 0.0
    target_start_date: date | None = None
    strategic_score: int = 3
    value_score: int = 3
    urgency_score: int = 3
    risk_score: int = 3
    scoring_template_id: str | None = None
    status: str = PortfolioIntakeStatus.PROPOSED.value


@dataclass(frozen=True)
class PortfolioScenarioCreateCommand:
    name: str
    budget_limit: float | None = None
    capacity_limit_percent: float | None = None
    project_ids: tuple[str, ...] = ()
    intake_item_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class PortfolioDependencyCreateCommand:
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    summary: str = ""


class ProjectManagementPortfolioDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        portfolio_service: PortfolioService | None = None,
    ) -> None:
        self._project_service = project_service
        self._portfolio_service = portfolio_service

    def list_projects(self) -> tuple[PortfolioProjectOptionDescriptor, ...]:
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(
            PortfolioProjectOptionDescriptor(
                value=project.id,
                label=project.name,
            )
            for project in projects
        )

    def list_intake_statuses(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return tuple(
            PortfolioOptionDescriptor(
                value=status.value,
                label=status.value.replace("_", " ").title(),
            )
            for status in PortfolioIntakeStatus
        )

    def list_dependency_types(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return tuple(
            PortfolioOptionDescriptor(
                value=dependency_type.value,
                label=_dependency_type_label(dependency_type),
            )
            for dependency_type in DependencyType
        )

    def list_templates(self) -> tuple[PortfolioTemplateDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        templates = sorted(
            service.list_scoring_templates(),
            key=lambda template: ((not template.is_active), (template.name or "").casefold()),
        )
        return tuple(self._serialize_template(template) for template in templates)

    def list_intake_items(
        self,
        *,
        status: str | None = None,
    ) -> tuple[PortfolioIntakeDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        normalized_status = _coerce_intake_status(status) if status else None
        rows = sorted(
            service.list_intake_items(status=normalized_status),
            key=lambda item: (-int(item.composite_score or 0), (item.title or "").casefold()),
        )
        return tuple(self._serialize_intake_item(item) for item in rows)

    def list_scenarios(self) -> tuple[PortfolioScenarioDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        rows = sorted(
            service.list_scenarios(),
            key=lambda scenario: ((scenario.name or "").casefold(), scenario.created_at),
        )
        return tuple(self._serialize_scenario(scenario) for scenario in rows)

    def evaluate_scenario(
        self,
        scenario_id: str,
    ) -> PortfolioScenarioEvaluationDesktopDto:
        evaluation = self._require_portfolio_service().evaluate_scenario(
            str(scenario_id or "").strip()
        )
        return self._serialize_evaluation(evaluation)

    def compare_scenarios(
        self,
        base_scenario_id: str,
        candidate_scenario_id: str,
    ) -> PortfolioScenarioComparisonDesktopDto:
        comparison = self._require_portfolio_service().compare_scenarios(
            str(base_scenario_id or "").strip(),
            str(candidate_scenario_id or "").strip(),
        )
        return self._serialize_comparison(comparison)

    def list_heatmap(self) -> tuple[PortfolioHeatmapDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        return tuple(
            self._serialize_heatmap_row(row)
            for row in service.list_portfolio_heatmap()
        )

    def list_dependencies(self) -> tuple[PortfolioDependencyDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        return tuple(
            self._serialize_dependency(row)
            for row in service.list_project_dependencies()
        )

    def list_recent_actions(
        self,
        *,
        limit: int = 12,
    ) -> tuple[PortfolioRecentActionDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        return tuple(
            self._serialize_recent_action(row)
            for row in service.list_recent_pm_actions(limit=limit)
        )

    def create_scoring_template(
        self,
        command: PortfolioTemplateCreateCommand,
    ) -> PortfolioTemplateDesktopDto:
        template = self._require_portfolio_service().create_scoring_template(
            name=command.name,
            summary=command.summary,
            strategic_weight=command.strategic_weight,
            value_weight=command.value_weight,
            urgency_weight=command.urgency_weight,
            risk_weight=command.risk_weight,
            activate=command.activate,
        )
        return self._serialize_template(template)

    def activate_scoring_template(self, template_id: str) -> PortfolioTemplateDesktopDto:
        template = self._require_portfolio_service().activate_scoring_template(
            str(template_id or "").strip()
        )
        return self._serialize_template(template)

    def create_intake_item(
        self,
        command: PortfolioIntakeCreateCommand,
    ) -> PortfolioIntakeDesktopDto:
        item = self._require_portfolio_service().create_intake_item(
            title=command.title,
            sponsor_name=command.sponsor_name,
            summary=command.summary,
            requested_budget=command.requested_budget,
            requested_capacity_percent=command.requested_capacity_percent,
            target_start_date=command.target_start_date,
            strategic_score=command.strategic_score,
            value_score=command.value_score,
            urgency_score=command.urgency_score,
            risk_score=command.risk_score,
            scoring_template_id=command.scoring_template_id,
            status=_coerce_intake_status(command.status),
        )
        return self._serialize_intake_item(item)

    def create_scenario(
        self,
        command: PortfolioScenarioCreateCommand,
    ) -> PortfolioScenarioDesktopDto:
        scenario = self._require_portfolio_service().create_scenario(
            name=command.name,
            budget_limit=command.budget_limit,
            capacity_limit_percent=command.capacity_limit_percent,
            project_ids=list(command.project_ids),
            intake_item_ids=list(command.intake_item_ids),
            notes=command.notes,
        )
        return self._serialize_scenario(scenario)

    def create_project_dependency(
        self,
        command: PortfolioDependencyCreateCommand,
    ) -> PortfolioDependencyDesktopDto:
        service = self._require_portfolio_service()
        dependency = service.create_project_dependency(
            predecessor_project_id=command.predecessor_project_id,
            successor_project_id=command.successor_project_id,
            dependency_type=_coerce_dependency_type(command.dependency_type),
            summary=command.summary,
        )
        dependency_rows = service.list_project_dependencies()
        normalized_summary = (command.summary or "").strip()
        for row in sorted(
            dependency_rows,
            key=lambda item: getattr(item, "created_at", datetime.min),
            reverse=True,
        ):
            if (
                row.predecessor_project_id == dependency.predecessor_project_id
                and row.successor_project_id == dependency.successor_project_id
                and row.dependency_type == dependency.dependency_type
                and (row.summary or "").strip() == normalized_summary
            ):
                return self._serialize_dependency(row)
        raise RuntimeError("The created portfolio dependency could not be reloaded.")

    def remove_project_dependency(self, dependency_id: str) -> None:
        self._require_portfolio_service().remove_project_dependency(
            str(dependency_id or "").strip()
        )

    def _require_portfolio_service(self) -> PortfolioService:
        if self._portfolio_service is None:
            raise RuntimeError("Project management portfolio desktop API is not connected.")
        return self._portfolio_service

    @staticmethod
    def _serialize_template(template) -> PortfolioTemplateDesktopDto:
        return PortfolioTemplateDesktopDto(
            id=template.id,
            name=template.name,
            summary=template.summary or "",
            weight_summary=template.weight_summary,
            is_active=bool(template.is_active),
            strategic_weight=int(template.strategic_weight or 0),
            value_weight=int(template.value_weight or 0),
            urgency_weight=int(template.urgency_weight or 0),
            risk_weight=int(template.risk_weight or 0),
        )

    @staticmethod
    def _serialize_intake_item(item) -> PortfolioIntakeDesktopDto:
        return PortfolioIntakeDesktopDto(
            id=item.id,
            title=item.title,
            sponsor_name=item.sponsor_name,
            summary=item.summary or "",
            requested_budget=float(item.requested_budget or 0.0),
            requested_budget_label=_format_money(item.requested_budget),
            requested_capacity_percent=float(item.requested_capacity_percent or 0.0),
            requested_capacity_label=_format_percent(item.requested_capacity_percent),
            target_start_date=item.target_start_date,
            target_start_date_label=_format_date(item.target_start_date),
            status=item.status.value,
            status_label=item.status.value.replace("_", " ").title(),
            scoring_template_id=item.scoring_template_id or "",
            scoring_template_name=item.scoring_template_name or "",
            composite_score=int(item.composite_score or 0),
            version=int(item.version or 1),
        )

    @staticmethod
    def _serialize_scenario(scenario) -> PortfolioScenarioDesktopDto:
        return PortfolioScenarioDesktopDto(
            id=scenario.id,
            name=scenario.name,
            budget_limit=scenario.budget_limit,
            budget_limit_label=_format_money(scenario.budget_limit, fallback="No budget limit"),
            capacity_limit_percent=scenario.capacity_limit_percent,
            capacity_limit_label=_format_percent(
                scenario.capacity_limit_percent,
                fallback="No capacity limit",
            ),
            project_ids=tuple(scenario.project_ids or ()),
            intake_item_ids=tuple(scenario.intake_item_ids or ()),
            notes=scenario.notes or "",
            created_at_label=_format_datetime(scenario.created_at),
        )

    @staticmethod
    def _serialize_evaluation(evaluation) -> PortfolioScenarioEvaluationDesktopDto:
        status_parts: list[str] = []
        if evaluation.over_budget:
            status_parts.append("Over budget")
        if evaluation.over_capacity:
            status_parts.append("Over capacity")
        if not status_parts:
            status_parts.append("Within limits")
        return PortfolioScenarioEvaluationDesktopDto(
            scenario_id=evaluation.scenario_id,
            scenario_name=evaluation.scenario_name,
            summary=evaluation.summary,
            selected_projects_label=str(int(evaluation.selected_projects or 0)),
            selected_intake_items_label=str(int(evaluation.selected_intake_items or 0)),
            total_budget_label=_format_money(evaluation.total_budget),
            budget_limit_label=_format_money(
                evaluation.budget_limit,
                fallback="No budget limit",
            ),
            total_capacity_label=_format_percent(evaluation.total_capacity_percent),
            capacity_limit_label=_format_percent(
                evaluation.capacity_limit_percent,
                fallback="No capacity limit",
            ),
            available_capacity_label=_format_percent(evaluation.available_capacity_percent),
            intake_score_label=str(int(evaluation.intake_composite_score or 0)),
            status_label=" | ".join(status_parts),
        )

    @staticmethod
    def _serialize_comparison(comparison) -> PortfolioScenarioComparisonDesktopDto:
        return PortfolioScenarioComparisonDesktopDto(
            base_scenario_id=comparison.base_scenario_id,
            base_scenario_name=comparison.base_scenario_name,
            candidate_scenario_id=comparison.candidate_scenario_id,
            candidate_scenario_name=comparison.candidate_scenario_name,
            summary=comparison.summary,
            budget_delta_label=_format_signed_money(comparison.budget_delta),
            capacity_delta_label=_format_signed_percent(comparison.capacity_delta_percent),
            intake_score_delta_label=_format_signed_int(comparison.intake_score_delta),
            selected_projects_delta_label=_format_signed_int(comparison.selected_projects_delta),
            selected_intake_items_delta_label=_format_signed_int(
                comparison.selected_intake_items_delta
            ),
            added_project_names=tuple(comparison.added_project_names or ()),
            removed_project_names=tuple(comparison.removed_project_names or ()),
            added_intake_titles=tuple(comparison.added_intake_titles or ()),
            removed_intake_titles=tuple(comparison.removed_intake_titles or ()),
        )

    @staticmethod
    def _serialize_heatmap_row(row) -> PortfolioHeatmapDesktopDto:
        return PortfolioHeatmapDesktopDto(
            project_id=row.project_id,
            project_name=row.project_name,
            project_status_label=str(row.project_status or "").replace("_", " ").title(),
            late_tasks=int(row.late_tasks or 0),
            critical_tasks=int(row.critical_tasks or 0),
            peak_utilization_percent=float(row.peak_utilization_percent or 0.0),
            peak_utilization_label=_format_percent(row.peak_utilization_percent),
            cost_variance=float(row.cost_variance or 0.0),
            cost_variance_label=_format_signed_money(row.cost_variance),
            pressure_label=row.pressure_label or "Stable",
        )

    @staticmethod
    def _serialize_dependency(row) -> PortfolioDependencyDesktopDto:
        dependency_type = row.dependency_type
        return PortfolioDependencyDesktopDto(
            dependency_id=row.dependency_id,
            predecessor_project_id=row.predecessor_project_id,
            predecessor_project_name=row.predecessor_project_name,
            predecessor_project_status_label=str(row.predecessor_project_status or "").replace(
                "_",
                " ",
            ).title(),
            successor_project_id=row.successor_project_id,
            successor_project_name=row.successor_project_name,
            successor_project_status_label=str(row.successor_project_status or "").replace(
                "_",
                " ",
            ).title(),
            dependency_type=dependency_type.value,
            dependency_type_label=_dependency_type_label(dependency_type),
            summary=row.summary or "",
            pressure_label=row.pressure_label or "Stable",
            created_at_label=_format_datetime(row.created_at),
        )

    @staticmethod
    def _serialize_recent_action(row) -> PortfolioRecentActionDesktopDto:
        return PortfolioRecentActionDesktopDto(
            occurred_at_label=_format_datetime(row.occurred_at),
            project_name=row.project_name,
            actor_username=row.actor_username,
            action_label=row.action_label,
            summary=row.summary,
        )


def build_project_management_portfolio_desktop_api(
    *,
    project_service: ProjectService | None = None,
    portfolio_service: PortfolioService | None = None,
) -> ProjectManagementPortfolioDesktopApi:
    return ProjectManagementPortfolioDesktopApi(
        project_service=project_service,
        portfolio_service=portfolio_service,
    )


def _coerce_intake_status(
    value: str | PortfolioIntakeStatus | None,
) -> PortfolioIntakeStatus:
    if isinstance(value, PortfolioIntakeStatus):
        return value
    normalized_value = str(value or PortfolioIntakeStatus.PROPOSED.value).strip().upper()
    try:
        return PortfolioIntakeStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported portfolio intake status: {normalized_value}.") from exc


def _coerce_dependency_type(
    value: str | DependencyType | None,
) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized_value = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported portfolio dependency type: {normalized_value}.") from exc


def _dependency_type_label(dependency_type: DependencyType) -> str:
    mapping = {
        DependencyType.FINISH_TO_START: "Finish -> Start",
        DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
        DependencyType.START_TO_START: "Start -> Start",
        DependencyType.START_TO_FINISH: "Start -> Finish",
    }
    return mapping.get(dependency_type, dependency_type.value)


def _format_money(value: float | None, *, fallback: str = "0.00") -> str:
    if value is None:
        return fallback
    return f"{float(value):,.2f}"


def _format_signed_money(value: float | None) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):+,.2f}"


def _format_percent(value: float | None, *, fallback: str = "0.0%") -> str:
    if value is None:
        return fallback
    return f"{float(value):.1f}%"


def _format_signed_percent(value: float | None) -> str:
    if value is None:
        return "0.0%"
    return f"{float(value):+.1f}%"


def _format_signed_int(value: int | None) -> str:
    return f"{int(value or 0):+d}"


def _format_date(value: date | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.isoformat()


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


__all__ = [
    "PortfolioDependencyCreateCommand",
    "PortfolioDependencyDesktopDto",
    "PortfolioHeatmapDesktopDto",
    "PortfolioIntakeCreateCommand",
    "PortfolioIntakeDesktopDto",
    "PortfolioOptionDescriptor",
    "PortfolioProjectOptionDescriptor",
    "PortfolioRecentActionDesktopDto",
    "PortfolioScenarioComparisonDesktopDto",
    "PortfolioScenarioCreateCommand",
    "PortfolioScenarioDesktopDto",
    "PortfolioScenarioEvaluationDesktopDto",
    "PortfolioTemplateCreateCommand",
    "PortfolioTemplateDesktopDto",
    "ProjectManagementPortfolioDesktopApi",
    "build_project_management_portfolio_desktop_api",
]
