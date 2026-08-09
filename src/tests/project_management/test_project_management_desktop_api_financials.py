from datetime import date, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_financials_desktop_api,
)
from src.core.modules.project_management.domain.enums import CostType, ProjectStatus
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))


def _make_services() -> tuple:
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
    return api, project, task, cost_service


def test_project_management_financials_desktop_api_keeps_legacy_costs_read_only() -> None:
    api, project, task, cost_service = _make_services()

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.list_cost_types()[0].value == "LABOR"
    assert api.list_tasks(project.id)[0].label == "TASK-1  Cable Pull"

    created = cost_service.add_cost_item(
        project.id,
        description="Electrical material package",
        planned_amount=1500.0,
        task_id=task.id,
        cost_type=CostType.MATERIAL,
        committed_amount=900.0,
        actual_amount=450.0,
        incurred_date=date(2026, 5, 4),
        currency_code="eur",
    )
    listed = api.list_cost_items(project.id)
    assert created.cost_type == "MATERIAL"
    assert listed[0].planned_amount_label == "EUR 1,500.00"
    assert listed[0].task_name == "TASK-1  Cable Pull"

    assert created.id == listed[0].id
    assert not hasattr(api, "create_cost_item")
    assert not hasattr(api, "update_cost_item")
    assert not hasattr(api, "delete_cost_item")


def test_project_management_financials_desktop_api_builds_snapshot() -> None:
    api, project, task, _cost_service = _make_services()

    _cost_service.add_cost_item(
        project.id,
        description="Electrical material package rev A",
        planned_amount=1600.0,
        task_id=task.id,
        cost_type=CostType.MATERIAL,
        committed_amount=1000.0,
        actual_amount=650.0,
        incurred_date=date(2026, 5, 5),
        currency_code="usd",
    )
    snapshot = api.get_finance_snapshot(project.id)

    assert snapshot.budget_label == "EUR 5,000.00"
    assert snapshot.planned_label == "EUR 1,600.00"
    assert snapshot.ledger[0].reference_label == "Electrical material package rev A"
    assert snapshot.cashflow[0].period_key == "2026-05"
    assert snapshot.by_cost_type[0].label == "Material"
    assert snapshot.notes[0] == "Finance snapshot preview generated from PM financial services."


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(self, *, name: str, description: str = "",
                       status: "ProjectStatus | None" = None,
                       client_name: str | None = None,
                       client_contact: str | None = None,
                       planned_budget: float | None = None,
                       currency: str | None = None,
                       start_date: date | None = None,
                       end_date: date | None = None) -> Project:
        project = Project(
            id=f"proj-{self._next_id}", name=name, description=description,
            start_date=start_date, end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name, client_contact=client_contact,
            planned_budget=planned_budget,
            currency=(currency or "").strip().upper() or None, version=1,
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


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [t for t in self._tasks.values() if t.project_id == project_id]

    def create_task(self, *, project_id: str, name: str, code: str = "",
                    description: str = "", start_date: date | None = None,
                    duration_days: int | None = None, priority: int = 0,
                    deadline: date | None = None) -> Task:
        task = Task(
            id=f"task-{self._next_id}", project_id=project_id, name=name,
            code=code, description=description, start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days, priority=priority, deadline=deadline,
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
        return [i for i in self._items.values() if i.project_id == project_id]

    def add_cost_item(self, project_id: str, *, description: str,
                      planned_amount: float, task_id: str | None = None,
                      cost_type: CostType = CostType.OVERHEAD,
                      committed_amount: float = 0.0, actual_amount: float = 0.0,
                      incurred_date: date | None = None,
                      currency_code: str | None = None,
                      code: str = "") -> SimpleNamespace:
        item = SimpleNamespace(
            id=f"cost-{self._next_id}", project_id=project_id, task_id=task_id,
            description=description, code=code or f"CST-{self._next_id:04d}",
            planned_amount=planned_amount, committed_amount=committed_amount,
            actual_amount=actual_amount, cost_type=cost_type,
            incurred_date=incurred_date,
            currency_code=(currency_code or "").strip().upper() or None, version=1,
        )
        self._next_id += 1
        self._items[item.id] = item
        return item

    def update_cost_item(self, cost_id: str, *, description: str | None = None,
                         planned_amount: float | None = None,
                         committed_amount: float | None = None,
                         actual_amount: float | None = None,
                         cost_type: CostType | None = None,
                         incurred_date: date | None = None,
                         currency_code: str | None = None,
                         expected_version: int | None = None,
                         code: str | None = None) -> SimpleNamespace:
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
    def __init__(self, *, project_service: _FakeProjectService,
                 task_service: _FakeTaskService,
                 cost_service: _FakeCostService) -> None:
        self._ps = project_service
        self._ts = task_service
        self._cs = cost_service

    def get_finance_snapshot(self, project_id: str) -> SimpleNamespace:
        project = self._ps.get_project(project_id)
        items = self._cs.list_cost_items_for_project(project_id)
        budget = float(getattr(project, "planned_budget", 0.0) or 0.0)
        planned = sum(float(i.planned_amount or 0.0) for i in items)
        committed = sum(float(i.committed_amount or 0.0) for i in items)
        actual = sum(float(i.actual_amount or 0.0) for i in items)
        exposure = max(committed, actual)
        available = budget - exposure if budget > 0.0 else None
        task_lookup = {t.id: t.name for t in self._ts.list_tasks_for_project(project_id)}
        ledger = [SimpleNamespace(
            project_id=project_id, source_key=f"source-{i.id}",
            source_label="Direct Cost", cost_type=i.cost_type.value,
            stage="actual" if float(i.actual_amount or 0.0) > 0.0 else "planned",
            amount=float(i.actual_amount or i.planned_amount or 0.0),
            currency=i.currency_code or getattr(project, "currency", None),
            occurred_on=i.incurred_date, reference_type="cost_item",
            reference_id=i.id, reference_label=i.description,
            task_id=i.task_id, task_name=task_lookup.get(i.task_id or "", None),
            resource_id=None, resource_name=None, included_in_policy=True,
        ) for i in items]
        cashflow = [SimpleNamespace(
            period_key="2026-05", period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31), planned=planned, committed=committed,
            actual=actual, forecast=max(planned, committed),
            exposure=max(committed, actual),
        )]
        by_source = [SimpleNamespace(
            dimension="source", key="direct_cost", label="Direct Cost",
            planned=planned, committed=committed, actual=actual,
            forecast=max(planned, committed), exposure=max(committed, actual),
        )]
        totals_map: dict[str, dict[str, float]] = {}
        for i in items:
            b = totals_map.setdefault(i.cost_type.value,
                                      {"planned": 0.0, "committed": 0.0, "actual": 0.0})
            b["planned"] += float(i.planned_amount or 0.0)
            b["committed"] += float(i.committed_amount or 0.0)
            b["actual"] += float(i.actual_amount or 0.0)
        by_cost_type = [SimpleNamespace(
            dimension="cost_type", key=k, label=k.replace("_", " ").title(),
            planned=v["planned"], committed=v["committed"], actual=v["actual"],
            forecast=max(v["planned"], v["committed"]),
            exposure=max(v["committed"], v["actual"]),
        ) for k, v in totals_map.items()]
        return SimpleNamespace(
            project_id=project_id,
            project_currency=getattr(project, "currency", None),
            budget=budget, planned=planned, committed=committed,
            actual=actual, exposure=exposure, available=available,
            ledger=ledger, cashflow=cashflow, by_source=by_source,
            by_cost_type=by_cost_type, by_resource=[], by_task=[],
            notes=["Finance snapshot preview generated from PM financial services."],
        )
