import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.api.desktop.platform import DesktopApiResult
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    TaskStatus,
)
from src.core.platform.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until

from src.tests.project_management._task_presenter_test_helpers import (
    _FakeCollaborationService,
    _FakeTaskService,
    _FakeTaskTimesheetsDesktopApi,
    _build_tasks_catalog,
    _make_task_service,
)


def test_tasks_controller_initial_state_and_lazy_load(tmp_path: Path, qapp) -> None:
    task_service = _make_task_service()
    collaboration_service = _FakeCollaborationService()
    timesheets_api = _FakeTaskTimesheetsDesktopApi()
    catalog, settings = _build_tasks_catalog(tmp_path, task_service, collaboration_service, timesheets_api)

    controller = catalog.tasksWorkspace

    assert controller.workspace["routeId"] == "project_management.tasks"
    assert controller.overview["title"] == "Tasks"
    metrics_by_label = {m["label"]: m for m in controller.overview["metrics"]}
    assert metrics_by_label["Mentions"]["value"] == "0"
    assert metrics_by_label["Notifications"]["value"] == "0"
    assert metrics_by_label["Active now"]["value"] == "0"
    assert controller.canUndoTaskAction is False
    assert controller.canRedoTaskAction is False
    assert controller.projectOptions[0]["label"] == "All Projects"
    assert controller.projectOptions[1]["label"] == "Plant Upgrade"
    assert controller.selectedProjectId == ""
    assert controller.selectedTaskId == "task-1"
    assert controller.priorityOptions[0]["label"] == "All priorities"
    assert controller.scheduleOptions[0]["value"] == "all"
    assert controller.taskViewOptions == [{"value": "", "label": "Current Filters"}]
    assert controller.tasks["items"][0]["title"] == "Cable Pull"
    assert controller.selectedTask["title"] == "Cable Pull"
    assert controller.assignmentOptions == []
    assert controller.assignments["items"] == []
    assert controller.selectedAssignmentId == ""
    assert controller.dependencies["items"] == []
    assert controller.dependencyTypeOptions == []
    assert controller.dependencyTaskOptions == []
    assert controller.timePeriodOptions == []
    assert controller.timeEntries["items"] == []
    assert controller.collaborationMentionOptions == []
    assert controller.collaborationDocumentOptions == []
    assert controller.collaborationComments["items"] == []
    assert controller.collaborationPresence["items"] == []
    assert collaboration_service.touched_presence == []

    controller.activateTask("task-1")
    wait_until(qapp, lambda: controller.selectedTask["description"] == "Primary feeder cable installation.")

    assert controller.assignmentOptions == []
    assert controller.assignments["items"] == []
    assert controller.selectedAssignmentId == ""
    assert controller.dependencies["items"] == []
    assert controller.dependencyTypeOptions == []
    assert controller.dependencyTaskOptions == []
    assert collaboration_service.touched_presence == []

    controller.setTaskReviewActive(True)
    wait_until(
        qapp,
        lambda: collaboration_service.touched_presence
        and collaboration_service.touched_presence[-1] == ("task-1", "reviewing"),
    )

    controller.loadSelectedTaskAssignments()

    assert controller.assignmentOptions[0]["label"] == "Alex Taylor (90.00 EUR/hr)"
    assert controller.assignments["items"][0]["title"] == "Alex Taylor"
    assert controller.selectedAssignmentId == "assign-1"

    controller.loadSelectedTaskDependencies()

    assert controller.dependencies["items"][0]["title"] == "Punchlist Closeout"
    assert controller.dependencyTypeOptions[0]["value"] == "FS"
    assert controller.dependencyTaskOptions[0]["value"] == "task-2"

    controller.loadSelectedTaskTime()

    assert controller.timePeriodOptions[0]["value"] == "2026-05-01"
    assert controller.timeEntries["items"][0]["title"] == "2026-05-03"
    assert controller.timeAssignmentSummary["state"]["assignmentId"] == "assign-1"
    assert controller.selectedTimeEntry["fields"][0]["value"] == "2026-05-03"

    controller.loadSelectedTaskCollaboration()

    assert controller.collaborationMentionOptions[0]["value"] == "planner"
    assert controller.collaborationDocumentOptions[0]["value"] == "doc-1"
    assert controller.collaborationComments["items"][0]["title"] == "@jamie"
    assert controller.collaborationPresence["items"][0]["title"] == "Alex Taylor (@planner)"
    assert controller.bulkStatusOptions[0]["value"] == "TODO"
