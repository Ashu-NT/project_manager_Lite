pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.AnchoredPopup {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var workspaceController: null
    property var state: null
    required property var anchorItem

    // ── Layout ───────────────────────────────────────────────────────────
    width: 260
    padding: Theme.AppTheme.marginMd
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingSm

        // ── Title ────────────────────────────────────────────────────────
        AppControls.Label {
            text: "Saved Views"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }

        // ── View selector ────────────────────────────────────────────────
        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.workspaceController ? (root.workspaceController.taskViewOptions || []) : []
            textRole: "label"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root.state
                ? root.state.optionIndexForValue(
                    root.workspaceController ? (root.workspaceController.taskViewOptions || []) : [],
                    root.workspaceController ? root.workspaceController.selectedTaskViewName : ""
                )
                : 0
            onActivated: function(index) {
                const options = root.workspaceController
                    ? (root.workspaceController.taskViewOptions || [])
                    : []
                if (root.workspaceController !== null && options[index]) {
                    root.workspaceController.selectTaskView(String(options[index].value || ""))
                }
            }
        }

        // ── Apply button ─────────────────────────────────────────────────
        AppControls.PrimaryButton {
            Layout.fillWidth: true
            text: "Apply View"
            iconName: "register"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            onClicked: {
                if (root.workspaceController !== null) {
                    root.workspaceController.applySelectedTaskView()
                }
                root.close()
            }
        }
    }
}
