from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog


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

