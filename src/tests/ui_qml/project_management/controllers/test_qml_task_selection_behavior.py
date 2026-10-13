from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)


def test_task_bulk_selection_methods_do_not_refresh_workspace(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.tasksWorkspace
    refresh_calls: list[str] = []

    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller.setTaskBulkSelection("task-1", True)
    controller.setTaskBulkSelection("task-2", True)
    controller.selectVisibleTasks()
    controller.clearTaskBulkSelection()

    assert refresh_calls == []


def test_task_list_selection_does_not_start_review_presence(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.tasksWorkspace
    sync_calls: list[str] = []

    monkeypatch.setattr(
        controller.collaborationController,
        "sync_review_presence",
        lambda task_id: sync_calls.append(str(task_id)),
    )

    controller.selectTask("task-1")

    assert sync_calls == []


def test_task_discussion_pager_forwards_through_workspace_facade(monkeypatch) -> None:
    controller = ProjectManagementWorkspaceCatalog().tasksWorkspace
    calls: list[tuple[str, str, int]] = []

    def page(task_id: str, number: int) -> dict[str, object]:
        calls.append(("page", task_id, number))
        return {"ok": True}

    def size(task_id: str, number: int) -> dict[str, object]:
        calls.append(("size", task_id, number))
        return {"ok": True}

    monkeypatch.setattr(controller.collaborationController, "requestCommentPage", page)
    monkeypatch.setattr(controller.collaborationController, "requestCommentPageSize", size)

    assert controller.requestCommentPage("task-1", 2) == {"ok": True}
    assert controller.requestCommentPageSize("task-1", 50) == {"ok": True}
    assert calls == [("page", "task-1", 2), ("size", "task-1", 50)]

