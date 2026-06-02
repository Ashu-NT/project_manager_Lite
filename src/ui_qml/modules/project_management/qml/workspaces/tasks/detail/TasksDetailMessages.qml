pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var workspaceController: null
    property bool visible: true

    // ── Layout ───────────────────────────────────────────────────────────
    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        // ── Error message ────────────────────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.visible
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        // ── Success message ──────────────────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.visible
                && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }
    }
}
