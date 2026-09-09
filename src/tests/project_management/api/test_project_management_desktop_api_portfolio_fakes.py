from datetime import date, datetime, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_portfolio_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    ProjectStatus,
    TaskStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
    PortfolioRecentAction,
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.projects.project import Project


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        status: "ProjectStatus | None" = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        financial_currency_code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def update_project(
        self,
        project_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
    ) -> Project:
        project = self._projects[project_id]
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if start_date is not None:
            project.start_date = start_date
        if end_date is not None:
            project.end_date = end_date
        if client_name is not None:
            project.client_name = client_name
        if client_contact is not None:
            project.client_contact = client_contact
        project.version += 1
        return project

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

    def activate_scoring_template(self, template_id: str) -> PortfolioScoringTemplate:
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

    def create_intake_item(
        self,
        *,
        title: str,
        sponsor_name: str,
        summary: str = "",
        requested_budget: float = 0.0,
        requested_capacity_percent: float = 0.0,
        target_start_date: date | None = None,
        strategic_score: int = 3,
        value_score: int = 3,
        urgency_score: int = 3,
        risk_score: int = 3,
        scoring_template_id: str | None = None,
        status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED,
    ) -> PortfolioIntakeItem:
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
