from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QDialog

from core.platform.common.exceptions import ConcurrencyError
from core.platform.common.models import TaskStatus
from ui.modules.project_management.cost.actions import CostActionsMixin
from ui.modules.project_management.project.actions import ProjectActionsMixin
from ui.modules.project_management.resource.actions import ResourceActionsMixin
from ui.modules.project_management.task.actions import TaskActionsMixin


def test_project_update_rejects_stale_expected_version(services):
    ps = services["project_service"]

    project = ps.create_project("Lock Project")
    updated = ps.update_project(project.id, name="Lock Project v2")

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        ps.update_project(project.id, name="stale", expected_version=1)


def test_task_update_rejects_stale_expected_version(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Task Lock Project")
    task = ts.create_task(
        project.id,
        "Task A",
        start_date=date(2026, 2, 24),
        duration_days=2,
    )
    updated = ts.update_task(task.id, name="Task A v2")

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        ts.update_task(task.id, name="stale", expected_version=1)


def test_resource_update_rejects_stale_expected_version(services):
    rs = services["resource_service"]

    resource = rs.create_resource("Dev A", hourly_rate=100.0)
    updated = rs.update_resource(resource.id, role="Engineer")

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        rs.update_resource(resource.id, role="stale", expected_version=1)


def test_cost_update_rejects_stale_expected_version(services):
    ps = services["project_service"]
    cs = services["cost_service"]

    project = ps.create_project("Cost Lock Project")
    item = cs.add_cost_item(
        project_id=project.id,
        description="Travel",
        planned_amount=1000.0,
    )
    updated = cs.update_cost_item(item.id, actual_amount=250.0)

    assert updated.version == 2
    with pytest.raises(ConcurrencyError):
        cs.update_cost_item(item.id, actual_amount=300.0, expected_version=1)


def test_task_edit_action_passes_expected_version(monkeypatch):
    calls: list[dict] = []

    class _TaskService:
        def update_task(self, **kwargs):
            calls.append(("task", kwargs))
            return SimpleNamespace(version=kwargs["expected_version"] + 1)

        def update_progress(self, **kwargs):
            calls.append(("progress", kwargs))

    class _Dialog:
        def __init__(self, _parent, task=None):
            self.name = task.name
            self.description = task.description
            self.start_date = task.start_date
            self.duration_days = task.duration_days
            self.status = task.status
            self.priority = task.priority
            self.deadline = task.deadline
            self.status_transition_kwargs = {}

        def exec(self):
            return QDialog.Accepted

    class _Probe(TaskActionsMixin):
        def __init__(self):
            self._task_service = _TaskService()
            self._resource_service = None
            self._project_resource_service = None
            self._task = SimpleNamespace(
                id="task-1",
                version=7,
                name="Task A",
                description="desc",
                start_date=date(2026, 1, 1),
                duration_days=2,
                status=TaskStatus.TODO,
                priority=1,
                deadline=date(2026, 1, 3),
            )
            self.reloaded = False

        def _get_selected_task(self):
            return self._task

        def reload_tasks(self):
            self.reloaded = True

    monkeypatch.setattr("ui.modules.project_management.task.actions.TaskEditDialog", _Dialog)
    probe = _Probe()

    probe.edit_task()

    assert calls[0][0] == "task"
    assert calls[0][1]["expected_version"] == 7
    assert probe.reloaded is True


def test_project_edit_action_passes_expected_version(monkeypatch):
    calls: list[dict] = []

    class _ProjectService:
        def update_project(self, **kwargs):
            calls.append(kwargs)

    class _Dialog:
        def __init__(self, _parent, project=None):
            self.name = project.name
            self.description = project.description
            self.client_name = project.client_name
            self.client_contact = project.client_contact
            self.planned_budget = project.planned_budget
            self.currency = project.currency
            self.status = project.status
            self.start_date = project.start_date
            self.end_date = project.end_date

        def exec(self):
            return QDialog.Accepted

    class _Probe(ProjectActionsMixin):
        def __init__(self):
            self._project_service = _ProjectService()
            self._project = SimpleNamespace(
                id="project-1",
                version=4,
                name="Project A",
                description="desc",
                client_name="Client",
                client_contact="Contact",
                planned_budget=100.0,
                currency="USD",
                status=SimpleNamespace(value="PLANNED"),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 10),
            )
            self.reloaded = False

        def _get_selected_project(self):
            return self._project

        def reload_projects(self):
            self.reloaded = True

    monkeypatch.setattr("ui.modules.project_management.project.actions.ProjectEditDialog", _Dialog)
    probe = _Probe()

    probe.edit_project()

    assert calls[0]["expected_version"] == 4
    assert probe.reloaded is True


def test_resource_edit_action_passes_expected_version(monkeypatch):
    calls: list[dict] = []

    class _ResourceService:
        def update_resource(self, **kwargs):
            calls.append(kwargs)

    class _Dialog:
        def __init__(self, _parent, resource=None, employee_service=None):
            _ = employee_service
            self.name = resource.name
            self.role = resource.role
            self.hourly_rate = resource.hourly_rate
            self.capacity_percent = resource.capacity_percent
            self.address = resource.address
            self.contact = resource.contact
            self.worker_type = resource.worker_type
            self.employee_id = resource.employee_id
            self.is_active = resource.is_active
            self.cost_type = resource.cost_type
            self.currency_code = resource.currency_code

        def exec(self):
            return QDialog.Accepted

    class _Probe(ResourceActionsMixin):
        def __init__(self):
            self._resource_service = _ResourceService()
            self._employee_service = None
            self._resource = SimpleNamespace(
                id="resource-1",
                version=5,
                name="Resource A",
                role="Engineer",
                hourly_rate=120.0,
                capacity_percent=100.0,
                address="",
                contact="",
                worker_type="EXTERNAL",
                employee_id=None,
                is_active=True,
                cost_type="LABOR",
                currency_code="USD",
            )
            self.reloaded = False

        def _get_selected_resource(self):
            return self._resource

        def reload_resources(self):
            self.reloaded = True

    monkeypatch.setattr("ui.modules.project_management.resource.actions.ResourceEditDialog", _Dialog)
    probe = _Probe()

    probe.edit_resource()

    assert calls[0]["expected_version"] == 5
    assert probe.reloaded is True


def test_cost_edit_action_passes_expected_version(monkeypatch):
    calls: list[dict] = []

    class _CostService:
        def update_cost_item(self, **kwargs):
            calls.append(kwargs)

    class _Dialog:
        def __init__(self, _parent, project=None, tasks=None, cost_item=None):
            _ = (project, tasks)
            self.description = cost_item.description
            self.actual_amount = cost_item.actual_amount
            self.planned_amount = cost_item.planned_amount
            self.committed_amount = cost_item.committed_amount
            self.cost_type = cost_item.cost_type
            self.incurred_date_value = cost_item.incurred_date
            self.currency_code = cost_item.currency_code

        def exec(self):
            return QDialog.Accepted

    class _Probe(CostActionsMixin):
        def __init__(self):
            self._cost_service = _CostService()
            self._current_project = None
            self._project_tasks = []
            self._item = SimpleNamespace(
                id="cost-1",
                version=6,
                description="Travel",
                actual_amount=10.0,
                planned_amount=20.0,
                committed_amount=15.0,
                cost_type="OTHER",
                incurred_date=date(2026, 1, 4),
                currency_code="USD",
            )
            self.reloaded = False

        def _current_project_id(self):
            return "project-1"

        def _get_selected_cost(self):
            return self._item

        def reload_costs(self):
            self.reloaded = True

    monkeypatch.setattr("ui.modules.project_management.cost.actions.CostEditDialog", _Dialog)
    probe = _Probe()

    probe.edit_cost_item()

    assert calls[0]["expected_version"] == 6
    assert probe.reloaded is True

