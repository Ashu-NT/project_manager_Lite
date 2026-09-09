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
from src.core.modules.project_management.contracts.reads.register import (
    RegisterCatalogReadItem,
    RegisterCatalogReadPage,
    RegisterCatalogSummary,
)
from src.core.modules.project_management.contracts.reads import ReadSort


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

    def query_catalog_page(
        self,
        *,
        project_id=None,
        entry_type=None,
        status=None,
        severity=None,
        search_text="",
        page=1,
        page_size=25,
        sort_key="triage",
        sort_direction="asc",
        **_kwargs,
    ) -> RegisterCatalogReadPage:
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"title"},
            default_key="triage",
        )
        scope = [
            entry for entry in self._entries.values()
            if project_id is None or entry.project_id == project_id
        ]
        filtered = [
            entry for entry in scope
            if (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
            and (
                not search_text
                or search_text.casefold() in entry.title.casefold()
                or search_text.casefold() in entry.description.casefold()
            )
        ]
        if sort.key == "triage":
            filtered.sort(key=lambda entry: entry.triage_key(date.today()))
        else:
            filtered.sort(
                key=lambda entry: (entry.title.casefold(), entry.id),
                reverse=sort.direction.value == "desc",
            )
        active_statuses = {
            RegisterEntryStatus.OPEN,
            RegisterEntryStatus.IN_PROGRESS,
            RegisterEntryStatus.MITIGATED,
        }
        active = [entry for entry in filtered if entry.status in active_statuses]
        urgent = sorted(active, key=lambda entry: entry.triage_key(date.today()))
        offset = (page - 1) * page_size
        to_item = lambda entry: RegisterCatalogReadItem(
            entry=entry,
            project_name=entry.project_id,
        )
        return RegisterCatalogReadPage(
            items=tuple(to_item(entry) for entry in filtered[offset:offset + page_size]),
            urgent_items=tuple(to_item(entry) for entry in urgent[:5]),
            filtered_total=len(filtered),
            page=page,
            page_size=page_size,
            summary=RegisterCatalogSummary(
                scope_total=len(scope),
                scope_risk_total=sum(
                    1 for entry in scope if entry.entry_type == RegisterEntryType.RISK
                ),
                open_risks=sum(
                    1 for entry in active if entry.entry_type == RegisterEntryType.RISK
                ),
                open_issues=sum(
                    1 for entry in active if entry.entry_type == RegisterEntryType.ISSUE
                ),
                pending_changes=sum(
                    1 for entry in filtered
                    if entry.entry_type == RegisterEntryType.CHANGE
                    and entry.status in {RegisterEntryStatus.OPEN, RegisterEntryStatus.IN_PROGRESS}
                ),
                active=len(active),
                critical=sum(
                    1 for entry in filtered
                    if entry.severity == RegisterEntrySeverity.CRITICAL
                ),
                overdue=sum(1 for entry in active if entry.is_overdue_on(date.today())),
            ),
            sort=sort,
        )


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

    register_controller.setTypeFilter("all")
    register_controller.setEntrySort("title", 1)

    assert register_controller.entrySortKey == "title"
    assert register_controller.entrySortDirection == 1
    assert [item["title"] for item in register_controller.entries["items"]] == [
        "Permit handoff blocked",
        "Critical supplier dependency",
        "Additional cable tray scope",
    ]
