"""ProjectManagementPortfolioDesktopApi — thin portfolio desktop facade."""

from __future__ import annotations

from typing import TypeVar

from src.core.modules.project_management.api.desktop.portfolio.builders.option_builder import (
    build_dependency_type_options,
    build_intake_status_options,
    build_project_options,
)
from src.core.modules.project_management.api.desktop.portfolio.models.options import (
    PortfolioOptionDescriptor,
    PortfolioProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.portfolio.utils.intake_status_utils import (
    coerce_intake_status,
)
from src.core.modules.project_management.application.common.pagination import (
    PaginatedResult,
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
from src.core.modules.project_management.application.portfolio.dto.responses.capacity import (
    PortfolioCapacityResourceDto,
)
from src.core.modules.project_management.application.portfolio.dto.responses.executive import (
    PortfolioExecutiveSnapshot,
)
from src.core.modules.project_management.application.portfolio.dto.responses.intake import (
    PortfolioIntakePageResponse,
    PortfolioIntakeResponse,
)
from src.core.modules.project_management.application.portfolio.dto.responses.scenarios import (
    PortfolioScenarioResponse,
)
from src.core.modules.project_management.application.portfolio.dto.responses.templates import (
    PortfolioTemplateResponseDto,
)
from src.core.modules.project_management.application.portfolio.queries import (
    PortfolioDependencyQueryHandler,
    PortfolioExecutiveQueryHandler,
    PortfolioIntakeQueryHandler,
    PortfolioScenarioQueryHandler,
    PortfolioTemplateQueryHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioProjectDependencyView,
    PortfolioRecentAction,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
)
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

    def list_projects(self) -> tuple[PortfolioProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_intake_statuses(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return build_intake_status_options()

    def list_dependency_types(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return build_dependency_type_options()

    def list_templates(self) -> tuple[PortfolioTemplateResponseDto, ...]:
        service = self._portfolio_template_query
        if service is None:
            return ()
        templates = sorted(
            service.list_scoring_templates(),
            key=lambda t: ((not t.is_active), (t.name or "").casefold()),
        )
        return tuple(templates)

    def list_intake_items(self, *, status: str | None = None) -> tuple[PortfolioIntakeResponse, ...]:
        query = self._portfolio_intake_query
        if query is None:
            return ()
        normalized_status = coerce_intake_status(status) if status else None
        rows = sorted(
            query.list_intake_items(status=normalized_status),
            key=lambda i: (-int(i.composite_score or 0), (i.title or "").casefold()),
        )
        return tuple(rows)

    def list_intake_items_page(
        self,
        *,
        status: str | None = None,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "updatedAt",
        sort_direction: str = "desc",
    ) -> PortfolioIntakePageResponse:
        query = self._portfolio_intake_query
        if query is None:
            return PortfolioIntakePageResponse(
                page=page, page_size=page_size, sort_key=sort_key,
                sort_direction=sort_direction, search_text=search_text,
            )
        normalized_status = coerce_intake_status(status) if status else None
        return query.list_intake_items_page(
            status=normalized_status,
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def list_dependencies_page(
        self,
        *,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "updatedAt",
        sort_direction: str = "desc",
    ) -> PaginatedResult[PortfolioProjectDependencyView]:
        service = self._portfolio_dependency_query
        if service is None:
            return PortfolioExecutiveQueryHandler.empty_page(page=page, page_size=page_size)
        result = service.list_project_dependencies_page(
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return result

    def list_scenarios(self) -> tuple[PortfolioScenarioResponse, ...]:
        service = self._portfolio_scenario_query
        if service is None:
            return ()
        rows = sorted(
            service.list_scenarios(),
            key=lambda s: ((s.name or "").casefold(), s.created_at),
        )
        return tuple(rows)

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        return _require(self._portfolio_scenario_query).evaluate_scenario(str(scenario_id or "").strip())

    def compare_scenarios(
        self, base_scenario_id: str, candidate_scenario_id: str
    ) -> PortfolioScenarioComparison:
        return _require(self._portfolio_scenario_query).compare_scenarios(
                str(base_scenario_id or "").strip(),
                str(candidate_scenario_id or "").strip(),
        )

    def list_heatmap(self) -> tuple[PortfolioExecutiveRow, ...]:
        service = self._portfolio_executive_query
        if service is None:
            return ()
        return tuple(service.list_portfolio_heatmap())

    def list_top_at_risk_projects(self) -> tuple[PortfolioExecutiveRow, ...]:
        """Bounded/top_n analytical projection -- ranks pressure across the
        complete authorized project scope. Never derived from a paginated
        Heatmap page; see PortfolioExecutiveQueryHandler.list_top_at_risk_projects."""
        service = self._portfolio_executive_query
        if service is None:
            return ()
        return tuple(service.list_top_at_risk_projects())

    def list_heatmap_page(
        self,
        *,
        search_text: str = "",
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> PaginatedResult[PortfolioExecutiveRow]:
        service = self._portfolio_executive_query
        if service is None:
            return PaginatedResult(items=[], page=page, page_size=page_size, total=0)
        normalized_status = _coerce_project_status(status)
        result = service.list_portfolio_heatmap_page(
            search_text=search_text,
            status=normalized_status,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return result

    def get_executive_snapshot(self) -> PortfolioExecutiveSnapshot:
        """Portfolio-wide aggregates for the Executive tab. Computes the full
        accessible-scope heatmap once and derives both the bounded Top At-Risk
        ranking and the hot-project count from that single scan -- see
        PortfolioExecutiveSnapshot."""
        executive = self._portfolio_executive_query
        dependencies = self._portfolio_dependency_query
        if executive is None or dependencies is None:
            return PortfolioExecutiveQueryHandler.empty_snapshot()
        return executive.get_executive_snapshot(dependencies)

    def list_dependencies(self) -> tuple[PortfolioProjectDependencyView, ...]:
        service = self._portfolio_dependency_query
        if service is None:
            return ()
        return tuple(service.list_project_dependencies())

    def list_recent_actions(self, *, limit: int = 12) -> tuple[PortfolioRecentAction, ...]:
        service = self._portfolio_executive_query
        if service is None:
            return ()
        return tuple(service.list_recent_pm_actions(limit=limit))

    def create_scoring_template(self, command: PortfolioTemplateCreateCommand) -> PortfolioTemplateResponseDto:
        return _require(self._portfolio_template_commands).create_scoring_template(command)

    def activate_scoring_template(self, command: PortfolioTemplateActivateCommand) -> PortfolioTemplateResponseDto:
        return _require(self._portfolio_template_commands).activate_scoring_template(command)

    def create_intake_item(self, command: PortfolioIntakeCreateCommand) -> PortfolioIntakeResponse:
        return _require(self._portfolio_intake_commands).create_intake_item(command)

    def create_scenario(self, command: PortfolioScenarioCreateCommand) -> PortfolioScenarioResponse:
        return _require(self._portfolio_scenario_commands).create_scenario(command)

    def create_project_dependency(self, command: PortfolioDependencyCreateCommand) -> PortfolioProjectDependencyView:
        return _require(self._portfolio_dependency_commands).create_project_dependency(
            command,
            query=_require(self._portfolio_dependency_query),
        )

    def remove_project_dependency(self, command: PortfolioDependencyRemoveCommand) -> None:
        _require(self._portfolio_dependency_commands).remove_project_dependency(command)

    def update_intake_item_status(self, command: PortfolioIntakeUpdateCommand) -> PortfolioIntakeResponse:
        return _require(self._portfolio_intake_commands).update_intake_item(command)

    def build_capacity_pool(self) -> tuple[PortfolioCapacityResourceDto, ...]:
        if self._portfolio_executive_query is None:
            return ()
        return self._portfolio_executive_query.query_capacity_pool()



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


__all__ = ['ProjectManagementPortfolioDesktopApi']
