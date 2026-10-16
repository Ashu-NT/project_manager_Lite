
from datetime import date
from src.core.modules.project_management.application.risk.mappers.entries import map_register_entry

from src.core.modules.project_management.api.desktop import (
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.mappers.project import (
    map_project_response,
)
from src.core.modules.project_management.application.risk.dto.commands.register_entries import (
    RegisterEntryCreateCommand,
    RegisterEntryDeleteCommand,
    RegisterEntryUpdateCommand,
)
from src.core.modules.project_management.domain.enums import (
    ProjectStatus,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


def test_project_management_register_desktop_api_mutates_register_entries() -> None:
    project_service = _FakeProjectService()
    project_alpha = project_service.create_project(ProjectCreateCommand(name="Plant Upgrade", description="Replace switchgear and commission the new line."))
    project_beta = project_service.create_project(ProjectCreateCommand(name="Warehouse Retrofit", description="Upgrade lighting and controls."))
    register_service = _FakeRegisterService()
    api = build_project_management_register_desktop_api(
        project_service=project_service,
        register_query=register_service,
        register_lifecycle_commands=register_service,
    )

    assert [option.label for option in api.list_projects()] == [
        "Plant Upgrade",
        "Warehouse Retrofit",
    ]
    assert api.list_entry_types()[0].value == "RISK"
    assert api.list_statuses()[1].label == "In Progress"
    assert api.list_severities()[0].label == "Low"

    created = api.create_entry(
        RegisterEntryCreateCommand(
            project_id=project_alpha.id,
            entry_type="RISK",
            title="Critical supplier dependency",
            description="Long-lead switchgear still needs the final release note.",
            severity="CRITICAL",
            status="OPEN",
            owner_name="Lead Planner",
            due_date=date(2026, 5, 2),
            impact_summary="Commissioning could slip by one week.",
            response_plan="Expedite vendor review and approve alternates.",
        )
    )
    api.create_entry(
        RegisterEntryCreateCommand(
            project_id=project_beta.id,
            entry_type="ISSUE",
            title="Permit handoff blocked",
            description="Permit package is still pending city review.",
            severity="HIGH",
            status="IN_PROGRESS",
            owner_name="Project Engineer",
            due_date=date(2026, 5, 6),
            impact_summary="Site mobilization is at risk.",
            response_plan="Escalate with local authority and track daily.",
        )
    )

    listed = api.list_entries()

    assert created.project_id == project_alpha.id
    assert listed[0].severity == "CRITICAL"
    assert listed[0].is_overdue is True

    updated = api.update_entry(
        RegisterEntryUpdateCommand(
            entry_id=created.id,
            project_id=project_alpha.id,
            entry_type="RISK",
            title="Critical supplier dependency mitigated",
            description="Final release note received from the vendor.",
            severity="HIGH",
            status="MITIGATED",
            owner_name="Lead Planner",
            due_date=date(2026, 5, 5),
            impact_summary="Residual risk remains on late freight handling.",
            response_plan="Confirm shipping lane and daily ETA tracking.",
            expected_version=register_service.get_entry(created.id).version,
        )
    )

    assert updated.title == "Critical supplier dependency mitigated"
    assert updated.status == "MITIGATED"
    assert api.list_entries(project_id=project_beta.id)[0].project_id == project_beta.id

    api.delete_entry(RegisterEntryDeleteCommand(created.id))

    assert {entry.id for entry in api.list_entries()} == {"reg-2"}


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

    def update_project(self, project_id: str, **kwargs) -> Project:
        project = self._projects[project_id]
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        project.version += 1
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]


class _FakeRegisterService:
    def __init__(self) -> None:
        self._entries: dict[str, RegisterEntry] = {}
        self._next_id = 1

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[RegisterEntry]:
        entries = [
            entry
            for entry in self._entries.values()
            if (project_id is None or entry.project_id == project_id)
            and (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
        ]
        return [map_register_entry(entry, project_name_by_id={}, as_of=date.today()) for entry in sorted(entries, key=lambda entry: entry.triage_key(date.today()))]

    def create_entry(self, command: RegisterEntryCreateCommand) -> RegisterEntry:
        project_id = command.project_id
        entry_type = command.entry_type
        title = command.title
        description = command.description
        severity = command.severity
        status = command.status
        owner_name = command.owner_name
        due_date = command.due_date
        impact_summary = command.impact_summary
        response_plan = command.response_plan
        code = command.code
        entry = RegisterEntry(
            id=f"reg-{self._next_id}",
            project_id=project_id,
            entry_type=entry_type,
            title=title,
            code=code or f"REG-{self._next_id:04d}",
            description=description,
            severity=severity,
            status=status,
            owner_name=owner_name,
            due_date=due_date,
            impact_summary=impact_summary,
            response_plan=response_plan,
            version=1,
        )
        self._next_id += 1
        self._entries[entry.id] = entry
        return map_register_entry(entry, project_name_by_id={}, as_of=date.today())

    def update_entry(self, command: RegisterEntryUpdateCommand) -> RegisterEntry:
        entry_id = command.entry_id
        entry_type = command.entry_type
        title = command.title
        description = command.description
        severity = command.severity
        status = command.status
        owner_name = command.owner_name
        due_date = command.due_date
        impact_summary = command.impact_summary
        response_plan = command.response_plan
        code = command.code
        entry = self._entries[entry_id]
        if code is not None and code.strip():
            entry.code = code
        if entry_type is not None:
            entry.entry_type = entry_type
        if title is not None:
            entry.title = title
        if description is not None:
            entry.description = description
        if severity is not None:
            entry.severity = severity
        if status is not None:
            entry.status = status
        if owner_name is not None:
            entry.owner_name = owner_name
        entry.due_date = due_date
        if impact_summary is not None:
            entry.impact_summary = impact_summary
        if response_plan is not None:
            entry.response_plan = response_plan
        entry.version += 1
        return entry

    def delete_entry(self, command: RegisterEntryDeleteCommand) -> None:
        entry_id = command.entry_id
        del self._entries[entry_id]

    def get_entry(self, entry_id: str) -> RegisterEntry:
        return self._entries[entry_id]
