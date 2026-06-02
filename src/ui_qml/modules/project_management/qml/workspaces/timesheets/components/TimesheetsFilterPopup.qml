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
    property var anchorItem: null

    anchorItem: root.anchorItem
    width: 280
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
            text: "Project"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }
        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
            textRole: "label"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root.state
                ? root.state.optionIndexForValue(
                    root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                    root.workspaceController ? root.workspaceController.selectedProjectId : "all")
                : 0
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.selectProject(String(opts[index].value || "all"))
            }
        }

        AppControls.Label {
            text: "Assignment"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }
        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
            textRole: "label"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root.state
                ? root.state.optionIndexForValue(
                    root.workspaceController ? (root.workspaceController.assignmentOptions || []) : [],
                    root.workspaceController ? root.workspaceController.selectedAssignmentId : "")
                : 0
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.selectAssignment(String(opts[index].value || ""))
            }
        }

        AppControls.Label {
            text: "Period"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }
        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.workspaceController ? (root.workspaceController.periodOptions || []) : []
            textRole: "label"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root.state
                ? root.state.optionIndexForValue(
                    root.workspaceController ? (root.workspaceController.periodOptions || []) : [],
                    root.workspaceController ? root.workspaceController.selectedPeriodStart : "")
                : 0
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.periodOptions || []) : []
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.selectPeriod(String(opts[index].value || ""))
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                Layout.fillWidth: true
                text: "Clear"
                iconName: "close"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject("all")
                        root.workspaceController.selectAssignment("")
                        root.workspaceController.selectPeriod("")
                    }
                    root.close()
                }
            }
            AppControls.SecondaryButton {
                Layout.fillWidth: true
                text: "Close"
                iconName: "close"
                onClicked: root.close()
            }
        }
    }
}
