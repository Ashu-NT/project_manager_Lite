"""Selection must only ever change through an explicit `selectProject()` call.
`resolve_selected_project_id()` must never fall back to `filtered_projects[0].id` when the
requested id isn't in the current page's items -- a page turn that can no longer see the
previously selected row must clear the selection, never substitute a different project."""

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
