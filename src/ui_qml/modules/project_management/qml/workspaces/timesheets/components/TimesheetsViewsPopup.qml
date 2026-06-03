pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.AnchoredPopup {
    id: root

    property var workspaceController: null
    property var state: null
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

        AppControls.Label {
            text: "View"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }

        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.workspaceController ? (root.workspaceController.queueStatusOptions || []) : []
            textRole: "label"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root.state
                ? root.state.optionIndexForValue(
                    root.workspaceController ? (root.workspaceController.queueStatusOptions || []) : [],
                    root.workspaceController ? root.workspaceController.selectedQueueStatus : "SUBMITTED")
                : 0
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.queueStatusOptions || []) : []
                if (root.workspaceController !== null && opts[index]) {
                    root.workspaceController.setQueueStatus(String(opts[index].value || "SUBMITTED"))
                    root.close()
                }
            }
        }
    }
}
