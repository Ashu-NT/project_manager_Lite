
from datetime import datetime

from src.core.modules.project_management.application.portfolio.dto.commands.intake import (
    PortfolioIntakeCreateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.scoring_templates import (
    PortfolioTemplateActivateCommand,
    PortfolioTemplateCreateCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.mappers.project import (
    map_project_response,
)
from src.core.modules.project_management.domain.enums import (
    ProjectStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioRecentAction,
    PortfolioScenario,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.projects.project import Project


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return [map_project_response(project) for project in self._projects.values()]

    def create_project(self, command: ProjectCreateCommand) -> ProjectResponse:
        project = Project(
            id=f"proj-{self._next_id}",
            name=command.name,
            description=command.description,
            start_date=command.start_date,
            end_date=command.end_date,
            status=ProjectStatus(command.status),
            client_name=command.client_name,
            client_contact=command.client_contact,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return map_project_response(project)

    def get_project(self, project_id: str) -> Project | None:
        project = self._projects.get(project_id)
        return None if project is None else map_project_response(project)

    def update_project(self, command: ProjectUpdateCommand) -> ProjectResponse:
        project = self._projects[command.project_id]
        if command.name is not None:
            project.name = command.name
        if command.description is not None:
            project.description = command.description
        if command.status is not None:
            project.status = ProjectStatus(command.status)
        if command.start_date is not None:
            project.start_date = command.start_date
        if command.end_date is not None:
            project.end_date = command.end_date
        if command.client_name is not None:
            project.client_name = command.client_name
        if command.client_contact is not None:
            project.client_contact = command.client_contact
        project.version += 1
        return map_project_response(project)

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]


class _FakePortfolioServiceBase:
    def __init__(self, project_service: _FakeProjectService) -> None:
        self._project_service = project_service
        self._templates: dict[str, PortfolioScoringTemplate] = {}
        self._intake_items: dict[str, PortfolioIntakeItem] = {}
        self._scenarios: dict[str, PortfolioScenario] = {}
        self._dependencies: dict[str, PortfolioProjectDependency] = {}
        self._actions: list[PortfolioRecentAction] = []

    def list_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        return list(self._templates.values())

    def create_scoring_template(self, command: PortfolioTemplateCreateCommand) -> PortfolioScoringTemplate:
        name = command.name
        summary = command.summary
        strategic_weight = command.strategic_weight
        value_weight = command.value_weight
        urgency_weight = command.urgency_weight
        risk_weight = command.risk_weight
        activate = command.activate
        if activate:
            for existing in self._templates.values():
                existing.is_active = False
        template = PortfolioScoringTemplate(
            id=f"tpl-{len(self._templates) + 1}",
            name=name,
            organization_id="org-1",
            summary=summary,
            strategic_weight=strategic_weight,
            value_weight=value_weight,
            urgency_weight=urgency_weight,
            risk_weight=risk_weight,
            is_active=activate,
            created_at=datetime(2026, 5, 1, 9, 0),
            updated_at=datetime(2026, 5, 1, 9, 0),
        )
        self._templates[template.id] = template
        self._append_action("Template created", "Portfolio", summary or name)
        return template

    def activate_scoring_template(self, command: PortfolioTemplateActivateCommand) -> PortfolioScoringTemplate:
        template_id = command.template_id
        for existing in self._templates.values():
            existing.is_active = existing.id == template_id
        template = self._templates[template_id]
        self._append_action("Template activated", "Portfolio", template.name)
        return template

    def list_intake_items(self, *, status: PortfolioIntakeStatus | None = None) -> list[PortfolioIntakeItem]:
        rows = list(self._intake_items.values())
        if status is not None:
            rows = [row for row in rows if row.status == status]
        return rows

    def create_intake_item(self, command: PortfolioIntakeCreateCommand) -> PortfolioIntakeItem:
        title = command.title
        sponsor_name = command.sponsor_name
        summary = command.summary
        requested_budget = command.requested_budget
        requested_capacity_percent = command.requested_capacity_percent
        target_start_date = command.target_start_date
        strategic_score = command.strategic_score
        value_score = command.value_score
        urgency_score = command.urgency_score
        risk_score = command.risk_score
        scoring_template_id = command.scoring_template_id
        status = command.status
        template = (
            self._templates.get(str(scoring_template_id or "").strip())
            if scoring_template_id
            else next((row for row in self._templates.values() if row.is_active), None)
        )
        item = PortfolioIntakeItem(
            id=f"intake-{len(self._intake_items) + 1}",
            title=title,
            sponsor_name=sponsor_name,
            organization_id="org-1",
            summary=summary,
            requested_budget=requested_budget,
            requested_capacity_percent=requested_capacity_percent,
            target_start_date=target_start_date,
            strategic_score=strategic_score,
            value_score=value_score,
            urgency_score=urgency_score,
            risk_score=risk_score,
            scoring_template_id=template.id if template is not None else "",
            scoring_template_name=template.name if template is not None else "Balanced PMO",
            strategic_weight=getattr(template, "strategic_weight", 3),
            value_weight=getattr(template, "value_weight", 2),
            urgency_weight=getattr(template, "urgency_weight", 2),
            risk_weight=getattr(template, "risk_weight", 1),
            status=status,
            created_at=datetime(2026, 5, 1, 10, 0),
            updated_at=datetime(2026, 5, 1, 10, 0),
            version=1,
        )
        self._intake_items[item.id] = item
        self._append_action("Intake created", "Portfolio", item.title)
        return item

    def _append_action(self, action_label: str, project_name: str, summary: str) -> None:
        self._actions.append(
            PortfolioRecentAction(
                occurred_at=datetime(2026, 5, 3, 9, len(self._actions)),
                project_name=project_name,
                actor_username="alex",
                action_label=action_label,
                summary=summary,
            )
        )
