from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QSignalSpy, QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


@pytest.mark.parametrize(
    "width,height",
    [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)],
)
def test_collaboration_composer_keeps_draft_identity_and_search_within_viewport(
    qapp, width: int, height: int
) -> None:
    engine = create_qml_engine()
    base = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksDialogHost.qml"
    ).resolve()
    component = QQmlComponent(engine)
    component.setData(
        b'''
import QtQuick
import QtQuick.Controls
import "dialogs" as TaskDialogs
Window {
    visible: true
    TaskDialogs.TaskCollaborationComposerDialog {
        objectName: "composer"
        taskData: ({ state: { taskId: "task-1", name: "Task" } })
        submissionId: "stable-draft-id"
    }
}
''',
        QUrl.fromLocalFile(str(base)),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None
    try:
        window.setWidth(width)
        window.setHeight(height)
        window.show()
        dialog = window.findChild(QObject, "composer")
        assert dialog is not None
        mention_requests = QSignalSpy(dialog.mentionSearchRequested)
        document_requests = QSignalSpy(dialog.documentSearchRequested)
        dialog.open()
        QTest.qWait(100)

        assert dialog.property("opened")
        assert dialog.property("submissionId") == "stable-draft-id"
        assert mention_requests.count() >= 1
        assert document_requests.count() >= 1
        assert 0 < dialog.property("height") <= height
        assert 0 <= dialog.property("x") <= width - dialog.property("width")
        assert 0 <= dialog.property("y") <= height - dialog.property("height")

        mention_search = dialog.findChild(QObject, "taskMentionSearch")
        document_search = dialog.findChild(QObject, "taskDocumentSearch")
        assert mention_search is not None and document_search is not None
        mention_search.setProperty("text", "planner")
        document_search.setProperty("text", "checklist")
        QTest.qWait(300)
        assert mention_requests.at(mention_requests.count() - 1)[0] == "planner"
        assert document_requests.at(document_requests.count() - 1)[0] == "checklist"
        assert dialog.property("submissionId") == "stable-draft-id"
    finally:
        window.close()
        window.deleteLater()
