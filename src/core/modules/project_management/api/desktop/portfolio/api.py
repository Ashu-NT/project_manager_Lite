"""ProjectManagementPortfolioDesktopApi — thin portfolio desktop facade."""

from __future__ import annotations
from datetime import datetime

from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.portfolio.queries.portfolio_executive import (
    TOP_AT_RISK_PROJECTS_LIMIT,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import PortfolioResourcePoolService
from src.core.modules.project_management.domain.enums import ProjectStatus

from src.core.modules.project_management.api.desktop.portfolio.models.capacity import PortfolioCapacityResourceDto
from src.core.modules.project_management.api.desktop.portfolio.models.dependencies import (
    PortfolioDependencyDesktopDto,
    PortfolioDependencyPageDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.executive import PortfolioExecutiveDesktopSnapshot
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
from src.core.modules.project_management.api.desktop.portfolio.models.recent_actions import PortfolioRecentActionDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.models.scenarios import (
    PortfolioScenarioComparisonDesktopDto,
    PortfolioScenarioDesktopDto,
    PortfolioScenarioEvaluationDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.templates import PortfolioTemplateDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.commands.create_dependency import PortfolioDependencyCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.commands.create_intake import PortfolioIntakeCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.commands.create_scenario import PortfolioScenarioCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.commands.create_template import PortfolioTemplateCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.builders.option_builder import (
    build_dependency_type_options,
    build_intake_status_options,
    build_project_options,
)
from src.core.modules.project_management.api.desktop.portfolio.builders.capacity_pool_builder import build_capacity_pool
from src.core.modules.project_management.api.desktop.portfolio.serializers.template_serializer import serialize_template
from src.core.modules.project_management.api.desktop.portfolio.serializers.intake_serializer import serialize_intake_item
from src.core.modules.project_management.api.desktop.portfolio.serializers.scenario_serializer import (
    serialize_comparison,
    serialize_evaluation,
    serialize_scenario,
)
from src.core.modules.project_management.api.desktop.portfolio.serializers.dependency_serializer import serialize_dependency
from src.core.modules.project_management.api.desktop.portfolio.serializers.heatmap_serializer import serialize_heatmap_row
from src.core.modules.project_management.api.desktop.portfolio.serializers.recent_action_serializer import serialize_recent_action
from src.core.modules.project_management.api.desktop.portfolio.utils.intake_status_utils import coerce_intake_status
from src.core.modules.project_management.api.desktop.common.dependency_presentation import coerce_dependency_type


class ProjectManagementPortfolioDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        portfolio_service: PortfolioService | None = None,
        pool_service: PortfolioResourcePoolService | None = None,
    ) -> None:
        self._project_service = project_service
        self._portfolio_service = portfolio_service
        self._pool_service = pool_service

    def list_projects(self) -> tuple[PortfolioProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_intake_statuses(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return build_intake_status_options()

    def list_dependency_types(self) -> tuple[PortfolioOptionDescriptor, ...]:
        return build_dependency_type_options()

    def list_templates(self) -> tuple[PortfolioTemplateDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        templates = sorted(
            service.list_scoring_templates(),
            key=lambda t: ((not t.is_active), (t.name or "").casefold()),
        )
        return tuple(serialize_template(t) for t in templates)

    def list_intake_items(self, *, status: str | None = None) -> tuple[PortfolioIntakeDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        normalized_status = coerce_intake_status(status) if status else None
        rows = sorted(
            service.list_intake_items(status=normalized_status),
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
        service = self._portfolio_service
        if service is None:
            return PortfolioIntakePageDto(
                page=page, page_size=page_size, sort_key=sort_key,
                sort_direction=sort_direction, search_text=search_text,
            )
        normalized_status = coerce_intake_status(status) if status else None
        result = service.list_intake_items_page(
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
        service = self._portfolio_service
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
        service = self._portfolio_service
        if service is None:
            return ()
        rows = sorted(
            service.list_scenarios(),
            key=lambda s: ((s.name or "").casefold(), s.created_at),
        )
        return tuple(serialize_scenario(s) for s in rows)

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluationDesktopDto:
        return serialize_evaluation(
            self._require_portfolio_service().evaluate_scenario(str(scenario_id or "").strip())
        )

    def compare_scenarios(
        self, base_scenario_id: str, candidate_scenario_id: str
    ) -> PortfolioScenarioComparisonDesktopDto:
        return serialize_comparison(
            self._require_portfolio_service().compare_scenarios(
                str(base_scenario_id or "").strip(),
                str(candidate_scenario_id or "").strip(),
            )
        )

    def list_heatmap(self) -> tuple[PortfolioHeatmapDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        return tuple(serialize_heatmap_row(row) for row in service.list_portfolio_heatmap())

    def list_top_at_risk_projects(self) -> tuple[PortfolioHeatmapDesktopDto, ...]:
        """Bounded/top_n analytical projection -- ranks pressure across the
        complete authorized project scope. Never derived from a paginated
        Heatmap page; see PortfolioService.list_top_at_risk_projects."""
        service = self._portfolio_service
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
        service = self._portfolio_service
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
        service = self._portfolio_service
        if service is None:
            return PortfolioExecutiveDesktopSnapshot()
        heatmap_rows = service.list_portfolio_heatmap()
        dependency_rows = service.list_project_dependencies(heatmap_rows=heatmap_rows)
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
        service = self._portfolio_service
        if service is None:
            return ()
        return tuple(serialize_dependency(row) for row in service.list_project_dependencies())

    def list_recent_actions(self, *, limit: int = 12) -> tuple[PortfolioRecentActionDesktopDto, ...]:
        service = self._portfolio_service
        if service is None:
            return ()
        return tuple(serialize_recent_action(row) for row in service.list_recent_pm_actions(limit=limit))

    def create_scoring_template(self, command: PortfolioTemplateCreateCommand) -> PortfolioTemplateDesktopDto:
        return serialize_template(
            self._require_portfolio_service().create_scoring_template(
                name=command.name,
                summary=command.summary,
                strategic_weight=command.strategic_weight,
                value_weight=command.value_weight,
                urgency_weight=command.urgency_weight,
                risk_weight=command.risk_weight,
                activate=command.activate,
            )
        )

    def activate_scoring_template(self, template_id: str) -> PortfolioTemplateDesktopDto:
        return serialize_template(
            self._require_portfolio_service().activate_scoring_template(str(template_id or "").strip())
        )

    def create_intake_item(self, command: PortfolioIntakeCreateCommand) -> PortfolioIntakeDesktopDto:
        return serialize_intake_item(
            self._require_portfolio_service().create_intake_item(
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
                status=coerce_intake_status(command.status),
            )
        )

    def create_scenario(self, command: PortfolioScenarioCreateCommand) -> PortfolioScenarioDesktopDto:
        return serialize_scenario(
            self._require_portfolio_service().create_scenario(
                name=command.name,
                budget_limit=command.budget_limit,
                capacity_limit_percent=command.capacity_limit_percent,
                project_ids=list(command.project_ids),
                intake_item_ids=list(command.intake_item_ids),
                notes=command.notes,
            )
        )

    def create_project_dependency(self, command: PortfolioDependencyCreateCommand) -> PortfolioDependencyDesktopDto:
        service = self._require_portfolio_service()
        dependency = service.create_project_dependency(
            predecessor_project_id=command.predecessor_project_id,
            successor_project_id=command.successor_project_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            summary=command.summary,
        )
        normalized_summary = (command.summary or "").strip()
        for row in sorted(
            service.list_project_dependencies(),
            key=lambda item: getattr(item, "created_at", datetime.min),
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

    def remove_project_dependency(self, dependency_id: str) -> None:
        self._require_portfolio_service().remove_project_dependency(str(dependency_id or "").strip())

    def update_intake_item_status(self, item_id: str, status: str) -> PortfolioIntakeDesktopDto:
        return serialize_intake_item(
            self._require_portfolio_service().update_intake_item(
                str(item_id or "").strip(),
                status=coerce_intake_status(status),
            )
        )

    def build_capacity_pool(self) -> tuple[PortfolioCapacityResourceDto, ...]:
        return build_capacity_pool(self._pool_service)

    def _require_portfolio_service(self) -> PortfolioService:
        if self._portfolio_service is None:
            raise RuntimeError("Project management portfolio desktop API is not connected.")
        return self._portfolio_service


def _coerce_project_status(value: str | None) -> ProjectStatus | None:
    normalized = str(value or "").strip().upper()
    if not normalized or normalized == "ALL":
        return None
    try:
        return ProjectStatus(normalized)
    except ValueError:
        return None


__all__ = ["ProjectManagementPortfolioDesktopApi"]
