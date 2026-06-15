from datetime import date, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_financials_desktop_api,
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    TaskStatus,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.domain.tasks.task import Task


def test_project_management_register_desktop_api_mutates_register_entries() -> None:
    project_service = _FakeProjectService()
    project_alpha = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    project_beta = project_service.create_project(
        name="Warehouse Retrofit",
        description="Upgrade lighting and controls.",
    )
    register_service = _FakeRegisterService()
    api = build_project_management_register_desktop_api(
        project_service=project_service,
        register_service=register_service,
    )

    assert [option.label for option in api.list_projects()] == [
        "Plant Upgrade",
        "Warehouse Retrofit",
    ]
    assert api.list_entry_types()[0].value == "RISK"
    assert api.list_statuses()[1].label == "In Progress"
    assert api.list_severities()[0].label == "Low"

    created = api.create_entry(
        SimpleNamespace(
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
        SimpleNamespace(
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

    assert created.project_name == "Plant Upgrade"
    assert listed[0].severity_label == "Critical"
    assert listed[0].is_overdue is True

    updated = api.update_entry(
        SimpleNamespace(
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
    assert api.list_entries(project_id=project_beta.id)[0].project_name == "Warehouse Retrofit"

    api.delete_entry(created.id)

    assert {entry.id for entry in api.list_entries()} == {"reg-2"}


def test_project_management_financials_desktop_api_mutates_cost_records_and_builds_snapshot() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
        planned_budget=5000.0,
        currency="eur",
    )
    task_service = _FakeTaskService()
    task = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=90,
        deadline=date(2026, 5, 7),
    )
    cost_service = _FakeCostService()
    finance_service = _FakeFinanceService(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
    )
    api = build_project_management_financials_desktop_api(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
        finance_service=finance_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.list_cost_types()[0].value == "LABOR"
    assert api.list_tasks(project.id)[0].label == "Cable Pull"

    created = api.create_cost_item(
        SimpleNamespace(
            project_id=project.id,
            description="Electrical material package",
            planned_amount=1500.0,
            task_id=task.id,
            cost_type="MATERIAL",
            committed_amount=900.0,
            actual_amount=450.0,
            incurred_date=date(2026, 5, 4),
            currency_code="eur",
        )
    )

    listed = api.list_cost_items(project.id)

    assert created.cost_type == "MATERIAL"
    assert listed[0].planned_amount_label == "EUR 1,500.00"
    assert listed[0].task_name == "Cable Pull"

    updated = api.update_cost_item(
        SimpleNamespace(
            cost_id=created.id,
            description="Electrical material package rev A",
            planned_amount=1600.0,
            task_id=task.id,
            cost_type="MATERIAL",
            committed_amount=1000.0,
            actual_amount=650.0,
            incurred_date=date(2026, 5, 5),
            currency_code="usd",
            expected_version=cost_service.get_item(created.id).version,
        )
    )

    assert updated.description == "Electrical material package rev A"
    assert updated.actual_amount_label == "USD 650.00"

    snapshot = api.get_finance_snapshot(project.id)

    assert snapshot.budget_label == "EUR 5,000.00"
    assert snapshot.planned_label == "EUR 1,600.00"
    assert snapshot.ledger[0].reference_label == "Electrical material package rev A"
    assert snapshot.cashflow[0].period_key == "2026-05"
    assert snapshot.by_cost_type[0].label == "Material"
    assert snapshot.notes[0] == "Finance snapshot preview generated from PM financial services."

    api.delete_cost_item(created.id)

    assert api.list_cost_items(project.id) == ()


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
        planned_budget: float | None = None,
        currency: str | None = None,
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
            planned_budget=planned_budget,
            currency=(currency or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

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
        self._entries: dict[str, SimpleNamespace] = {}
        self._next_id = 1

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[SimpleNamespace]:
        return [
            entry
            for entry in self._entries.values()
            if (project_id is None or entry.project_id == project_id)
            and (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
        ]

    def create_entry(
        self,
        project_id: str,
        *,
        entry_type: RegisterEntryType,
        title: str,
        description: str = "",
        severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM,
        status: RegisterEntryStatus = RegisterEntryStatus.OPEN,
        owner_name: str | None = None,
        due_date: date | None = None,
        impact_summary: str = "",
        response_plan: str = "",
        code: str = "",
    ) -> SimpleNamespace:
        entry = SimpleNamespace(
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
        return entry

    def update_entry(
        self,
        entry_id: str,
        *,
        expected_version: int | None = None,
        entry_type: RegisterEntryType | None = None,
        title: str | None = None,
        description: str | None = None,
        severity: RegisterEntrySeverity | None = None,
        status: RegisterEntryStatus | None = None,
        owner_name: str | None = None,
        due_date: date | None = None,
        impact_summary: str | None = None,
        response_plan: str | None = None,
        code: str | None = None,
    ) -> SimpleNamespace:
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

    def delete_entry(self, entry_id: str) -> None:
        del self._entries[entry_id]

    def get_entry(self, entry_id: str) -> SimpleNamespace:
        return self._entries[entry_id]


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def create_task(
        self,
        *,
        project_id: str,
        name: str,
        code: str = "",
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int = 0,
        deadline: date | None = None,
    ) -> Task:
        task = Task(
            id=f"task-{self._next_id}",
            project_id=project_id,
            name=name,
            code=code,
            description=description,
            start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days,
            priority=priority,
            deadline=deadline,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


class _FakeCostService:
    def __init__(self) -> None:
        self._items: dict[str, SimpleNamespace] = {}
        self._next_id = 1

    def list_cost_items_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [item for item in self._items.values() if item.project_id == project_id]

    def add_cost_item(
        self,
        project_id: str,
        *,
        description: str,
        planned_amount: float,
        task_id: str | None = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        code: str = "",
    ) -> SimpleNamespace:
        item = SimpleNamespace(
            id=f"cost-{self._next_id}",
            project_id=project_id,
            task_id=task_id,
            description=description,
            code=code or f"CST-{self._next_id:04d}",
            planned_amount=planned_amount,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            cost_type=cost_type,
            incurred_date=incurred_date,
            currency_code=(currency_code or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._items[item.id] = item
        return item

    def update_cost_item(
        self,
        cost_id: str,
        *,
        description: str | None = None,
        planned_amount: float | None = None,
        committed_amount: float | None = None,
        actual_amount: float | None = None,
        cost_type: CostType | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        expected_version: int | None = None,
        code: str | None = None,
    ) -> SimpleNamespace:
        item = self._items[cost_id]
        if code is not None and code.strip():
            item.code = code
        if description is not None:
            item.description = description
        if planned_amount is not None:
            item.planned_amount = planned_amount
        if committed_amount is not None:
            item.committed_amount = committed_amount
        if actual_amount is not None:
            item.actual_amount = actual_amount
        if cost_type is not None:
            item.cost_type = cost_type
        if incurred_date is not None:
            item.incurred_date = incurred_date
        if currency_code is not None:
            item.currency_code = (currency_code or "").strip().upper() or None
        item.version += 1
        return item

    def delete_cost_item(self, cost_id: str) -> None:
        del self._items[cost_id]

    def get_item(self, cost_id: str) -> SimpleNamespace:
        return self._items[cost_id]


class _FakeFinanceService:
    def __init__(
        self,
        *,
        project_service: _FakeProjectService,
        task_service: _FakeTaskService,
        cost_service: _FakeCostService,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._cost_service = cost_service

    def get_finance_snapshot(self, project_id: str) -> SimpleNamespace:
        project = self._project_service.get_project(project_id)
        items = self._cost_service.list_cost_items_for_project(project_id)
        budget = float(getattr(project, "planned_budget", 0.0) or 0.0)
        planned = sum(float(item.planned_amount or 0.0) for item in items)
        committed = sum(float(item.committed_amount or 0.0) for item in items)
        actual = sum(float(item.actual_amount or 0.0) for item in items)
        exposure = max(committed, actual)
        available = budget - exposure if budget > 0.0 else None
        task_lookup = {
            task.id: task.name for task in self._task_service.list_tasks_for_project(project_id)
        }
        ledger = [
            SimpleNamespace(
                project_id=project_id,
                source_key=f"source-{item.id}",
                source_label="Direct Cost",
                cost_type=item.cost_type.value,
                stage="actual" if float(item.actual_amount or 0.0) > 0.0 else "planned",
                amount=float(item.actual_amount or item.planned_amount or 0.0),
                currency=item.currency_code or getattr(project, "currency", None),
                occurred_on=item.incurred_date,
                reference_type="cost_item",
                reference_id=item.id,
                reference_label=item.description,
                task_id=item.task_id,
                task_name=task_lookup.get(item.task_id or "", None),
                resource_id=None,
                resource_name=None,
                included_in_policy=True,
            )
            for item in items
        ]
        cashflow = [
            SimpleNamespace(
                period_key="2026-05",
                period_start=date(2026, 5, 1),
                period_end=date(2026, 5, 31),
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=max(planned, committed),
                exposure=max(committed, actual),
            )
        ]
        by_source = [
            SimpleNamespace(
                dimension="source",
                key="direct_cost",
                label="Direct Cost",
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=max(planned, committed),
                exposure=max(committed, actual),
            )
        ]
        by_cost_type_totals: dict[str, dict[str, float]] = {}
        for item in items:
            bucket = by_cost_type_totals.setdefault(
                item.cost_type.value,
                {"planned": 0.0, "committed": 0.0, "actual": 0.0},
            )
            bucket["planned"] += float(item.planned_amount or 0.0)
            bucket["committed"] += float(item.committed_amount or 0.0)
            bucket["actual"] += float(item.actual_amount or 0.0)
        by_cost_type = [
            SimpleNamespace(
                dimension="cost_type",
                key=key,
                label=key.replace("_", " ").title(),
                planned=totals["planned"],
                committed=totals["committed"],
                actual=totals["actual"],
                forecast=max(totals["planned"], totals["committed"]),
                exposure=max(totals["committed"], totals["actual"]),
            )
            for key, totals in by_cost_type_totals.items()
        ]
        return SimpleNamespace(
            project_id=project_id,
            project_currency=getattr(project, "currency", None),
            budget=budget,
            planned=planned,
            committed=committed,
            actual=actual,
            exposure=exposure,
            available=available,
            ledger=ledger,
            cashflow=cashflow,
            by_source=by_source,
            by_cost_type=by_cost_type,
            by_resource=[],
            by_task=[],
            notes=["Finance snapshot preview generated from PM financial services."],
        )


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
