"""ProjectManagementPortfolioDesktopApi — thin portfolio desktop facade."""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

from src.core.modules.project_management.api.desktop.portfolio.builders.capacity_pool_builder import (
    build_capacity_pool,
)
from src.core.modules.project_management.api.desktop.portfolio.builders.option_builder import (
    build_dependency_type_options,
    build_intake_status_options,
    build_project_options,
)
from src.core.modules.project_management.api.desktop.portfolio.models.capacity import (
    PortfolioCapacityResourceDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.dependencies import (
    PortfolioDependencyDesktopDto,
    PortfolioDependencyPageDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.executive import (
    PortfolioExecutiveDesktopSnapshot,
)
from src.core.modules.project_management.api.desktop.portfolio.models.heatmap import (
    PortfolioHeatmapDesktopDto,
    PortfolioHeatmapPageDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.intake import (
    PortfolioIntakeDesktopDto,
    PortfolioIntakePageDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.options import (
    PortfolioOptionDescriptor,
    PortfolioProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.portfolio.models.recent_actions import (
    PortfolioRecentActionDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.scenarios import (
    PortfolioScenarioComparisonDesktopDto,
    PortfolioScenarioDesktopDto,
    PortfolioScenarioEvaluationDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.templates import (
    PortfolioTemplateDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.dependency_serializer import (
    serialize_dependency,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.heatmap_serializer import (
    serialize_heatmap_row,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.intake_serializer import (
    serialize_intake_item,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.recent_action_serializer import (
    serialize_recent_action,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.scenario_serializer import (
    serialize_comparison,
    serialize_evaluation,
    serialize_scenario,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.template_serializer import (
    serialize_template,
)
from src.core.modules.project_management.api.desktop.portfolio.utils.intake_status_utils import (
    coerce_intake_status,
)
from src.core.modules.project_management.application.portfolio.commands import (
    PortfolioDependencyCommandHandler,
    PortfolioIntakeCommandHandler,
    PortfolioScenarioCommandHandler,
    PortfolioTemplateCommandHandler,
)
from src.core.modules.project_management.application.portfolio.dto.commands.intake import (
    PortfolioIntakeCreateCommand,
    PortfolioIntakeUpdateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.project_dependencies import (
    PortfolioDependencyCreateCommand,
    PortfolioDependencyRemoveCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.scenarios import (
    PortfolioScenarioCreateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.scoring_templates import (
    PortfolioTemplateActivateCommand,
    PortfolioTemplateCreateCommand,
)
from src.core.modules.project_management.application.portfolio.queries import (
    PortfolioDependencyQueryHandler,
    PortfolioExecutiveQueryHandler,
    PortfolioIntakeQueryHandler,
    PortfolioScenarioQueryHandler,
    PortfolioTemplateQueryHandler,
)
from src.core.modules.project_management.application.portfolio.queries.portfolio_executive import (
    TOP_AT_RISK_PROJECTS_LIMIT,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolQueryHandler,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.common.exceptions import ConfigurationError


class ProjectManagementPortfolioDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectQueryHandler | None = None,
        portfolio_intake_query: PortfolioIntakeQueryHandler | None = None,
        portfolio_intake_commands: PortfolioIntakeCommandHandler | None = None,
        portfolio_template_query: PortfolioTemplateQueryHandler | None = None,
        portfolio_template_commands: PortfolioTemplateCommandHandler | None = None,
        portfolio_scenario_query: PortfolioScenarioQueryHandler | None = None,
        portfolio_scenario_commands: PortfolioScenarioCommandHandler | None = None,
        portfolio_dependency_query: PortfolioDependencyQueryHandler | None = None,
        portfolio_dependency_commands: PortfolioDependencyCommandHandler | None = None,
        portfolio_executive_query: PortfolioExecutiveQueryHandler | None = None,
        pool_service: PortfolioResourcePoolQueryHandler | None = None,
    ) -> None:
        self._project_service = project_service
        self._portfolio_intake_query = portfolio_intake_query
        self._portfolio_intake_commands = portfolio_intake_commands
        self._portfolio_template_query = portfolio_template_query
        self._portfolio_template_commands = portfolio_template_commands
        self._portfolio_scenario_query = portfolio_scenario_query
        self._portfolio_scenario_commands = portfolio_scenario_commands
        self._portfolio_dependency_query = portfolio_dependency_query
        self._portfolio_dependency_commands = portfolio_dependency_commands
        self._portfolio_executive_query = portfolio_executive_query
        self._pool_service = pool_service

    def list_projects(self) -> tuple[PortfolioProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_intake_statuses(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return build_intake_status_options()

    def list_dependency_types(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return build_dependency_type_options()

    def list_templates(self) -> tuple[PortfolioTemplateDesktopDto, ...]:
        service = self._portfolio_template_query
        if service is None:
            return ()
        templates = sorted(
            service.list_scoring_templates(),
            key=lambda t: ((not t.is_active), (t.name or "").casefold()),
        )
        return tuple(serialize_template(t) for t in templates)

    def list_intake_items(self, *, status: str | None = None) -> tuple[PortfolioIntakeDesktopDto, ...]:
        query = self._portfolio_intake_query
        if query is None:
            return ()
        normalized_status = coerce_intake_status(status) if status else None
        rows = sorted(
            query.list_intake_items(status=normalized_status),
            key=lambda i: (-int(i.composite_score or 0), (i.title or "").casefold()),
        )
        return tuple(serialize_intake_item(i) for i in rows)

    def list_intake_items_page(
        self,
        *,
        status: str | None = None,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "updatedAt",
        sort_direction: str = "desc",
    ) -> PortfolioIntakePageDto:
        query = self._portfolio_intake_query
        if query is None:
            return PortfolioIntakePageDto(
                page=page, page_size=page_size, sort_key=sort_key,
                sort_direction=sort_direction, search_text=search_text,
            )
        normalized_status = coerce_intake_status(status) if status else None
        result = query.list_intake_items_page(
            status=normalized_status,
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return PortfolioIntakePageDto(
            items=tuple(serialize_intake_item(row) for row in result.items),
            total=result.total or 0,
            page=result.page,
            page_size=result.page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
            search_text=search_text,
        )

    def list_dependencies_page(
        self,
        *,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "updatedAt",
        sort_direction: str = "desc",
    ) -> PortfolioDependencyPageDto:
        service = self._portfolio_dependency_query
        if service is None:
            return PortfolioDependencyPageDto(
                page=page, page_size=page_size, sort_key=sort_key,
                sort_direction=sort_direction, search_text=search_text,
            )
        result = service.list_project_dependencies_page(
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return PortfolioDependencyPageDto(
            items=tuple(serialize_dependency(row) for row in result.items),
            total=result.total or 0,
            page=result.page,
            page_size=result.page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
            search_text=search_text,
        )

    def list_scenarios(self) -> tuple[PortfolioScenarioDesktopDto, ...]:
        service = self._portfolio_scenario_query
        if service is None:
            return ()
        rows = sorted(
            service.list_scenarios(),
            key=lambda s: ((s.name or "").casefold(), s.created_at),
        )
        return tuple(serialize_scenario(s) for s in rows)

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluationDesktopDto:
        return serialize_evaluation(
            _require(self._portfolio_scenario_query).evaluate_scenario(str(scenario_id or "").strip())
        )

    def compare_scenarios(
        self, base_scenario_id: str, candidate_scenario_id: str
    ) -> PortfolioScenarioComparisonDesktopDto:
        return serialize_comparison(
            _require(self._portfolio_scenario_query).compare_scenarios(
                str(base_scenario_id or "").strip(),
                str(candidate_scenario_id or "").strip(),
            )
        )

    def list_heatmap(self) -> tuple[PortfolioHeatmapDesktopDto, ...]:
        service = self._portfolio_executive_query
        if service is None:
            return ()
        return tuple(serialize_heatmap_row(row) for row in service.list_portfolio_heatmap())

    def list_top_at_risk_projects(self) -> tuple[PortfolioHeatmapDesktopDto, ...]:
        """Bounded/top_n analytical projection -- ranks pressure across the
        complete authorized project scope. Never derived from a paginated
        Heatmap page; see PortfolioExecutiveQueryHandler.list_top_at_risk_projects."""
        service = self._portfolio_executive_query
        if service is None:
            return ()
        return tuple(serialize_heatmap_row(row) for row in service.list_top_at_risk_projects())

    def list_heatmap_page(
        self,
        *,
        search_text: str = "",
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> PortfolioHeatmapPageDto:
        service = self._portfolio_executive_query
        if service is None:
            return PortfolioHeatmapPageDto(
                page=page, page_size=page_size, sort_key=sort_key,
                sort_direction=sort_direction, search_text=search_text,
            )
        normalized_status = _coerce_project_status(status)
        result = service.list_portfolio_heatmap_page(
            search_text=search_text,
            status=normalized_status,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return PortfolioHeatmapPageDto(
            items=tuple(serialize_heatmap_row(row) for row in result.items),
            total=result.total or 0,
            page=result.page,
            page_size=result.page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
            search_text=search_text,
        )

    def get_executive_snapshot(self) -> PortfolioExecutiveDesktopSnapshot:
        """Portfolio-wide aggregates for the Executive tab. Computes the full
        accessible-scope heatmap once and derives both the bounded Top At-Risk
        ranking and the hot-project count from that single scan -- see
        PortfolioExecutiveDesktopSnapshot."""
        executive = self._portfolio_executive_query
        dependencies = self._portfolio_dependency_query
        if executive is None or dependencies is None:
            return PortfolioExecutiveDesktopSnapshot()
        heatmap_rows = executive.list_portfolio_heatmap()
        dependency_rows = dependencies.list_project_dependencies(heatmap_rows=heatmap_rows)
        hot_count = sum(1 for row in heatmap_rows if row.pressure_label == "Hot")
        return PortfolioExecutiveDesktopSnapshot(
            heatmap=tuple(serialize_heatmap_row(row) for row in heatmap_rows),
            dependencies=tuple(serialize_dependency(row) for row in dependency_rows),
            top_at_risk_projects=tuple(
                serialize_heatmap_row(row) for row in heatmap_rows[:TOP_AT_RISK_PROJECTS_LIMIT]
            ),
            hot_project_count=hot_count,
            dependency_count=len(dependency_rows),
        )

    def list_dependencies(self) -> tuple[PortfolioDependencyDesktopDto, ...]:
        service = self._portfolio_dependency_query
        if service is None:
            return ()
        return tuple(serialize_dependency(row) for row in service.list_project_dependencies())

    def list_recent_actions(self, *, limit: int = 12) -> tuple[PortfolioRecentActionDesktopDto, ...]:
        service = self._portfolio_executive_query
        if service is None:
            return ()
        return tuple(serialize_recent_action(row) for row in service.list_recent_pm_actions(limit=limit))

    def create_scoring_template(self, command: PortfolioTemplateCreateCommand) -> PortfolioTemplateDesktopDto:
        return serialize_template(
            _require(self._portfolio_template_commands).create_scoring_template(command)
        )

    def activate_scoring_template(self, command: PortfolioTemplateActivateCommand) -> PortfolioTemplateDesktopDto:
        return serialize_template(
            _require(self._portfolio_template_commands).activate_scoring_template(command)
        )

    def create_intake_item(self, command: PortfolioIntakeCreateCommand) -> PortfolioIntakeDesktopDto:
        return serialize_intake_item(
            _require(self._portfolio_intake_commands).create_intake_item(command)
        )

    def create_scenario(self, command: PortfolioScenarioCreateCommand) -> PortfolioScenarioDesktopDto:
        return serialize_scenario(
            _require(self._portfolio_scenario_commands).create_scenario(command)
        )

    def create_project_dependency(self, command: PortfolioDependencyCreateCommand) -> PortfolioDependencyDesktopDto:
        dependency = _require(self._portfolio_dependency_commands).create_project_dependency(command)
        normalized_summary = (command.summary or "").strip()
        for row in sorted(
            _require(self._portfolio_dependency_query).list_project_dependencies(),
            key=lambda item: getattr(item, "created_at", datetime.min),  # noqa: DTZ901 - fallback only
            reverse=True,
        ):
            if (
                row.predecessor_project_id == dependency.predecessor_project_id
                and row.successor_project_id == dependency.successor_project_id
                and row.dependency_type == dependency.dependency_type
                and (row.summary or "").strip() == normalized_summary
            ):
                return serialize_dependency(row)
        raise RuntimeError("The created portfolio dependency could not be reloaded.")

    def remove_project_dependency(self, command: PortfolioDependencyRemoveCommand) -> None:
        _require(self._portfolio_dependency_commands).remove_project_dependency(command)

    def update_intake_item_status(self, command: PortfolioIntakeUpdateCommand) -> PortfolioIntakeDesktopDto:
        return serialize_intake_item(
            _require(self._portfolio_intake_commands).update_intake_item(command)
        )

    def build_capacity_pool(self) -> tuple[PortfolioCapacityResourceDto, ...]:
        return build_capacity_pool(self._pool_service)



_HandlerT = TypeVar("_HandlerT")


def _require(handler: _HandlerT | None) -> _HandlerT:
    if handler is None:
        raise ConfigurationError("Project management portfolio desktop API is not connected.")
    return handler


def _coerce_project_status(value: str | None) -> ProjectStatus | None:
    normalized = str(value or "").strip().upper()
    if not normalized or normalized == "ALL":
        return None
    try:
        return ProjectStatus(normalized)
    except ValueError:
        return None


__all__ = ["ProjectManagementPortfolioDesktopApi"]
