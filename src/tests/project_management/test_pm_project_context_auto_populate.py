"""Direct product report: the PM project-context bar's search dropdown was
empty on first open (requiring the user to type a search before anything
appeared) and stayed stale after creating a new project mid-session (no
refresh trigger until a tenant/org switch or reauthentication). Fixed by
loading an initial page eagerly at construction and subscribing to the
"project" domain-change event PMWorkspaceNavigationController-adjacent
controllers already use."""

from __future__ import annotations

from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.controllers.common.pm_project_context_controller import (
    PMProjectContextController,
)


class _FakeProject:
    def __init__(self, project_id: str, name: str) -> None:
        self.id = project_id
        self.name = name
        self.code = ""
        self.status_label = "Active"


class _FakePage:
    def __init__(self, items):
        self.items = items


class _FakeProjectsApi:
    def __init__(self, projects):
        self._projects = {project.id: project for project in projects}

    def list_project_page(self, *, search_text="", **_kwargs):
        needle = str(search_text or "").casefold()
        items = [p for p in self._projects.values() if needle in p.name.casefold()]
        return _FakePage(items)

    def get_project(self, project_id):
        return self._projects.get(str(project_id or ""))

    def add(self, project: _FakeProject) -> None:
        self._projects[project.id] = project


def test_project_options_are_populated_on_construction_without_a_search() -> None:
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])

    controller = PMProjectContextController(projects_api=api)

    assert [option["label"] for option in controller.projectOptions] == ["Plant Upgrade"]


def test_project_options_refresh_when_a_project_domain_change_fires() -> None:
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    assert len(controller.projectOptions) == 1

    # Simulate a project being created elsewhere in the app (e.g. the
    # Projects capability's create-project command), which broadcasts a
    # "project" domain-change event on the "project_management" scope --
    # the same event Dashboard/Portfolio already subscribe to for their
    # own refresh.
    api.add(_FakeProject("p-2", "Harbor Expansion"))
    domain_events.project_changed.emit("p-2")

    assert {option["label"] for option in controller.projectOptions} == {
        "Plant Upgrade",
        "Harbor Expansion",
    }


def test_unrelated_domain_change_does_not_trigger_a_refresh() -> None:
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    refresh_count = {"n": 0}
    controller.projectOptionsChanged.connect(lambda: refresh_count.__setitem__("n", refresh_count["n"] + 1))

    domain_events.tasks_changed.emit("p-1")

    assert refresh_count["n"] == 0
