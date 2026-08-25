from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine


ROOT = Path(__file__).resolve().parents[2]
PM_QML = ROOT / "ui_qml/modules/project_management/qml"


def _read(relative_path: str) -> str:
    return (PM_QML / relative_path).read_text(encoding="utf-8")


def test_r5g_keeps_frozen_workload_navigation_and_task_time_owner() -> None:
    navigation = (
        ROOT
        / "ui_qml/modules/project_management/controllers/common/pm_workspace_navigation_controller.py"
    ).read_text(encoding="utf-8")
    task_detail = _read("workspaces/tasks/panels/TasksDetailPanel.qml")

    workload_entries = [
        line
        for line in navigation.splitlines()
        if '"group": "Workload Management"' in line
    ]
    assert len(workload_entries) == 2
    assert any('"id": "resources"' in line for line in workload_entries)
    assert any('"id": "review_queue"' in line for line in workload_entries)
    assert "TasksTimeEntriesSection" in task_detail


def test_r5g_filters_use_the_shared_centered_dialog_contract() -> None:
    resources_page = _read("workspaces/resources/ResourcesWorkspacePage.qml")
    resources_filter = _read(
        "workspaces/resources/components/ResourcesFilterPopup.qml"
    )
    queue_page = _read("workspaces/timesheets/TimesheetsWorkspacePage.qml")
    queue_filter = _read("workspaces/timesheets/components/TimesheetsFilterPopup.qml")

    assert "AppControls.CenteredDialog" in resources_filter
    assert "AppControls.CenteredDialog" in queue_filter
    assert "AppWidgets.AnchoredPopup" not in resources_filter
    assert "AppWidgets.AnchoredPopup" not in queue_filter
    assert "anchorItem: listPage.filterButtonItem" not in resources_page
    assert "anchorItem: listPage.filterButtonItem" not in queue_page
    assert "Popup.CloseOnEscape | Popup.CloseOnPressOutside" in resources_filter
    assert "Popup.CloseOnEscape | Popup.CloseOnPressOutside" in queue_filter


def test_r5g_review_queue_uses_one_responsive_inspector_authority() -> None:
    page = _read("workspaces/timesheets/TimesheetsWorkspacePage.qml")
    inspector = _read(
        "workspaces/timesheets/components/TimesheetReviewInspector.qml"
    )

    assert "Theme.AppTheme.inspectorWidth + 720" in page
    assert "root.width >= root._sideInspectorThreshold" in page
    assert "Window.width" not in page
    assert "selectedQueuePeriodId" in page
    assert "TimesheetReviewInspector" in page
    assert "SectionDetailPage" not in page
    assert "_detailOpen" not in page
    assert "AppWidgets.InspectorPanel" in inspector
    assert "state.detailActions" in page
    assert "expectedVersion" not in page


@pytest.mark.parametrize(
    ("width", "height"),
    [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)],
)
def test_r5g_review_queue_runtime_geometry(
    qapp, width: int, height: int
) -> None:
    messages: list[str] = []

    def capture_message(_message_type, _context, message: str) -> None:
        messages.append(str(message))

    previous_handler = qInstallMessageHandler(capture_message)
    page = None
    try:
        engine = create_qml_engine()
        source = PM_QML / "workspaces/timesheets/TimesheetsWorkspacePage.qml"
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(source.resolve())))
        page = component.create()
        assert page is not None, "\n".join(
            error.toString() for error in component.errors()
        )
        assert page.setProperty("width", width)
        assert page.setProperty("height", height)
        qapp.processEvents()

        queue = page.findChild(QObject, "timesheetReviewQueueListPage")
        filter_popup = page.findChild(QObject, "reviewQueueFilterPopup")
        assert queue is not None
        assert filter_popup is not None
        assert 0 < float(queue.property("width")) <= width
        assert 0 < float(queue.property("height")) <= height
        assert 0 < float(filter_popup.property("width")) <= width
        assert 0 < float(filter_popup.property("implicitHeight")) <= height
        filter_content = filter_popup.findChild(QObject, "reviewQueueFilterContent")
        filter_actions = filter_popup.findChild(QObject, "reviewQueueFilterActions")
        assert filter_content is not None
        assert filter_actions is not None
        assert float(filter_content.property("implicitWidth")) <= float(
            filter_popup.property("width")
        )
        assert float(filter_actions.property("implicitWidth")) <= float(
            filter_popup.property("width")
        )
        threshold = int(page.property("_sideInspectorThreshold"))
        assert bool(page.property("_useSideInspector")) is (width >= threshold)
    finally:
        if page is not None:
            page.deleteLater()
        qInstallMessageHandler(previous_handler)

    assert not any("managed by a layout" in message for message in messages), messages
    assert not any("is not a type" in message for message in messages), messages
    assert not any("ReferenceError" in message for message in messages), messages


def test_r5g_resources_centered_filter_fits_minimum_viewport(qapp) -> None:
    engine = create_qml_engine()
    source = PM_QML / "workspaces/resources/ResourcesWorkspacePage.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(source.resolve())))
    page = component.create()
    assert page is not None, "\n".join(error.toString() for error in component.errors())
    try:
        assert page.setProperty("width", 1024)
        assert page.setProperty("height", 640)
        qapp.processEvents()

        filter_popup = page.findChild(QObject, "resourcesFilterPopup")
        assert filter_popup is not None
        assert 0 < float(filter_popup.property("width")) <= 1024
        assert 0 < float(filter_popup.property("implicitHeight")) <= 640
        filter_content = filter_popup.findChild(QObject, "resourcesFilterContent")
        filter_actions = filter_popup.findChild(QObject, "resourcesFilterActions")
        assert filter_content is not None
        assert filter_actions is not None
        assert float(filter_content.property("implicitWidth")) <= float(
            filter_popup.property("width")
        )
        assert float(filter_actions.property("implicitWidth")) <= float(
            filter_popup.property("width")
        )
    finally:
        page.deleteLater()
