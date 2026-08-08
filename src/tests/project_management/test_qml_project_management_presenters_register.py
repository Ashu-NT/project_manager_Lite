from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.core.modules.project_management.api.desktop import (
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


class _FakeRegisterService:
    def __init__(self, entries: list[RegisterEntry] | None = None) -> None:
        self._entries = {entry.id: entry for entry in (entries or [])}

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
        return sorted(entries, key=lambda entry: entry.triage_key(date.today()))


def _build_register_record(
    *,
    entry_id,
    project_id,
    entry_type,
    title,
    description,
    severity,
    status,
    owner_name,
    due_date,
    impact_summary,
    response_plan,
    version,
) -> RegisterEntry:
    return RegisterEntry(
        id=entry_id,
        project_id=project_id,
        entry_type=entry_type,
        title=title,
        description=description,
        severity=severity,
        status=status,
        owner_name=owner_name,
        due_date=due_date,
        impact_summary=impact_summary,
        response_plan=response_plan,
        version=version,
    )


def test_project_management_workspace_catalog_exposes_typed_register_controller() -> None:
    register_api = build_project_management_register_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        register_service=_FakeRegisterService(
            [
                _build_register_record(
                    entry_id="reg-1",
                    project_id="proj-1",
                    entry_type=RegisterEntryType.RISK,
                    title="Critical supplier dependency",
                    description="Switchgear release note is still pending.",
                    severity=RegisterEntrySeverity.CRITICAL,
                    status=RegisterEntryStatus.OPEN,
                    owner_name="Lead Planner",
                    due_date=date(2026, 5, 2),
                    impact_summary="Commissioning could slip by one week.",
                    response_plan="Escalate with vendor and approve alternates.",
                    version=2,
                ),
                _build_register_record(
                    entry_id="reg-2",
                    project_id="proj-1",
                    entry_type=RegisterEntryType.CHANGE,
                    title="Additional cable tray scope",
                    description="New field route requires material and labor change.",
                    severity=RegisterEntrySeverity.MEDIUM,
                    status=RegisterEntryStatus.IN_PROGRESS,
                    owner_name="Project Engineer",
                    due_date=date(2026, 5, 7),
                    impact_summary="Budget exposure needs approval.",
                    response_plan="Issue estimate and submit change control.",
                    version=1,
                ),
                _build_register_record(
                    entry_id="reg-3",
                    project_id="proj-2",
                    entry_type=RegisterEntryType.ISSUE,
                    title="Permit handoff blocked",
                    description="Permit package is still pending city review.",
                    severity=RegisterEntrySeverity.HIGH,
                    status=RegisterEntryStatus.IN_PROGRESS,
                    owner_name="PM",
                    due_date=date(2026, 5, 6),
                    impact_summary="Mobilization is at risk.",
                    response_plan="Daily escalation with local authority.",
                    version=1,
                ),
            ]
        ),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_register=register_api,
        )
    )

    register_controller = catalog.registerWorkspace

    assert register_controller.workspace["routeId"] == "project_management.register"
    assert register_controller.typeOptions[1]["value"] == "RISK"
    assert register_controller.entries["items"][0]["title"] == "Critical supplier dependency"
    assert register_controller.selectedEntry["fields"][2]["label"] == "Impact"

    register_controller.setTypeFilter("RISK")

    assert [item["title"] for item in register_controller.entries["items"]] == [
        "Critical supplier dependency"
    ]

    register_controller.setTypeFilter("CHANGE")

    assert [item["title"] for item in register_controller.entries["items"]] == [
        "Additional cable tray scope"
    ]
