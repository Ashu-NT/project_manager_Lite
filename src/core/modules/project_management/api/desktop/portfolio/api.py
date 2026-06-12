"""ProjectManagementPortfolioDesktopApi — thin portfolio desktop facade."""

from __future__ import annotations
from datetime import datetime

from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import PortfolioResourcePoolService

from src.core.modules.project_management.api.desktop.portfolio.models.capacity import PortfolioCapacityResourceDto
from src.core.modules.project_management.api.desktop.portfolio.models.dependencies import PortfolioDependencyDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.models.heatmap import PortfolioHeatmapDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.models.intake import PortfolioIntakeDesktopDto
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
from src.core.modules.project_management.api.desktop.portfolio.utils.dependency_type_utils import coerce_dependency_type


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


__all__ = ["ProjectManagementPortfolioDesktopApi"]
