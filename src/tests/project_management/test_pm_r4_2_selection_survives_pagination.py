"""R4.2 checklist finding: `resolve_selected_project_id()` used to fall
back to `filtered_projects[0].id` whenever the requested id wasn't present
in the current page's items -- meaning a plain page turn (select a project
on page 1, then navigate to page 2) silently reassigned the selection to
an unrelated project the user never clicked. With the new inspector
actually surfacing "the selected project" on screen, this was no longer a
harmless no-op -- it would show the wrong project's details after a page
turn. Selection must only ever change through an explicit selectProject()
call; a refresh that can no longer see the previously selected row must
clear the selection, never substitute a different one."""

from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.projects.selection import (
    resolve_selected_project_id,
)


class _FakeProject:
    def __init__(self, project_id: str) -> None:
        self.id = project_id


def test_selection_clears_rather_than_reassigning_when_not_on_current_page() -> None:
    page_two_items = [_FakeProject("p-3"), _FakeProject("p-4")]

    resolved = resolve_selected_project_id("p-1", page_two_items)

    assert resolved == ""


def test_selection_is_preserved_when_still_on_current_page() -> None:
    page_items = [_FakeProject("p-1"), _FakeProject("p-2")]

    resolved = resolve_selected_project_id("p-1", page_items)

    assert resolved == "p-1"


def test_no_selection_stays_no_selection_rather_than_defaulting_to_first_row() -> None:
    page_items = [_FakeProject("p-1"), _FakeProject("p-2")]

    resolved = resolve_selected_project_id("", page_items)

    assert resolved == ""


def test_empty_page_with_a_requested_id_clears_selection() -> None:
    resolved = resolve_selected_project_id("p-1", [])

    assert resolved == ""
