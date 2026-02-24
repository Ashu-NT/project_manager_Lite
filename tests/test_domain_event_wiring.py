from datetime import date
from pathlib import Path

from core.models import DependencyType
from core.events.domain_events import domain_events


def test_project_create_emits_project_changed(services):
    ps = services["project_service"]
    seen: list[str] = []

    def _on_project_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.project_changed.connect(_on_project_changed)
    try:
        project = ps.create_project("Event Project", "")
    finally:
        domain_events.project_changed.disconnect(_on_project_changed)

    assert project.id in seen


def test_project_update_emits_project_changed(services):
    ps = services["project_service"]
    project = ps.create_project("Event Update Project", "")
    seen: list[str] = []

    def _on_project_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.project_changed.connect(_on_project_changed)
    try:
        ps.update_project(project.id, name="Event Update Project V2")
    finally:
        domain_events.project_changed.disconnect(_on_project_changed)

    assert seen == [project.id]


def test_task_create_dependency_assignment_emit_tasks_changed(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Event Task Ops", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2024, 1, 3), duration_days=2)
    resource = rs.create_resource("Event Dev", "Developer", hourly_rate=100.0)
    seen: list[str] = []

    def _on_tasks_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.tasks_changed.connect(_on_tasks_changed)
    try:
        t3 = ts.create_task(project.id, "Task C", start_date=date(2024, 1, 6), duration_days=1)
        ts.add_dependency(t1.id, t2.id, DependencyType.FINISH_TO_START, lag_days=0)
        ts.assign_resource(t3.id, resource.id, allocation_percent=50.0)
    finally:
        domain_events.tasks_changed.disconnect(_on_tasks_changed)

    assert seen.count(project.id) >= 3


def test_task_update_emits_tasks_changed(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Event Task Update", "")
    task = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    seen: list[str] = []

    def _on_tasks_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.tasks_changed.connect(_on_tasks_changed)
    try:
        ts.update_task(task.id, name="Task A Updated")
    finally:
        domain_events.tasks_changed.disconnect(_on_tasks_changed)

    assert seen == [project.id]


def test_cost_add_emits_costs_changed(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]

    project = ps.create_project("Event Cost", "")
    task = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=1)
    seen: list[str] = []

    def _on_costs_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.costs_changed.connect(_on_costs_changed)
    try:
        cs.add_cost_item(
            project_id=project.id,
            description="Capex",
            planned_amount=100.0,
            task_id=task.id,
        )
    finally:
        domain_events.costs_changed.disconnect(_on_costs_changed)

    assert seen == [project.id]


def test_resource_create_update_delete_emit_resources_changed(services):
    rs = services["resource_service"]
    seen: list[str] = []

    def _on_resources_changed(resource_id: str) -> None:
        seen.append(resource_id)

    domain_events.resources_changed.connect(_on_resources_changed)
    try:
        resource = rs.create_resource("Event Resource", "Analyst", hourly_rate=80.0)
        rs.update_resource(resource.id, name="Event Resource Updated")
        rs.delete_resource(resource.id)
    finally:
        domain_events.resources_changed.disconnect(_on_resources_changed)

    assert seen == [resource.id, resource.id, resource.id]


def test_report_tab_subscribes_to_project_changed_for_combo_refresh():
    text = (Path(__file__).resolve().parents[1] / "ui" / "report" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "domain_events.project_changed.connect(self._on_project_changed_event)" in text


def test_dashboard_subscribes_project_changes_to_catalog_refresh():
    text = (Path(__file__).resolve().parents[1] / "ui" / "dashboard" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "domain_events.project_changed.connect(self._on_project_catalog_changed)" in text


def test_tabs_subscribe_to_resources_changed_for_refresh():
    root = Path(__file__).resolve().parents[1]
    task_text = (root / "ui" / "task" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    cost_text = (root / "ui" / "cost" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    dash_text = (root / "ui" / "dashboard" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    project_text = (root / "ui" / "project" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "domain_events.resources_changed.connect(self._on_resources_changed)" in task_text
    assert "domain_events.resources_changed.connect(self._on_resources_changed)" in cost_text
    assert "domain_events.resources_changed.connect(self._on_resources_changed)" in dash_text
    assert "domain_events.resources_changed.connect(self._on_resources_changed_event)" in project_text
