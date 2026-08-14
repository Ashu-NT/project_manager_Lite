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
    width: 340
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
                    root.workspaceController ? root.workspaceController.selectedQueueProjectId : "all")
                : 0
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.setQueueProject(String(opts[index].value || "all"))
            }
        }

        AppControls.Label {
            text: "Resource"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }
        AppControls.ComboBox {
            Layout.fillWidth: true
            model: root.workspaceController ? (root.workspaceController.queueResourceOptions || []) : []
            textRole: "label"
            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root.state
                ? root.state.optionIndexForValue(
                    root.workspaceController ? (root.workspaceController.queueResourceOptions || []) : [],
                    root.workspaceController ? root.workspaceController.selectedQueueResourceId : "all")
                : 0
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.queueResourceOptions || []) : []
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.setQueueResource(String(opts[index].value || "all"))
            }
        }

        AppControls.Label {
            text: "Period start range"
            font.bold: true
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.DateField {
                id: periodFromField
                Layout.fillWidth: true
                placeholderText: "From"
                text: root.workspaceController ? root.workspaceController.queuePeriodStartFrom : ""
                popupBoundaryItem: root.contentItem
            }
            AppControls.DateField {
                id: periodToField
                Layout.fillWidth: true
                placeholderText: "To"
                text: root.workspaceController ? root.workspaceController.queuePeriodStartTo : ""
                popupBoundaryItem: root.contentItem
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
                        root.workspaceController.setQueueProject("all")
                        root.workspaceController.setQueueResource("all")
                        root.workspaceController.setQueuePeriodRange("", "")
                    }
                    root.close()
                }
            }
            AppControls.PrimaryButton {
                Layout.fillWidth: true
                text: "Apply"
                iconName: "approve"
                onClicked: {
                    if (root.workspaceController !== null)
                        root.workspaceController.setQueuePeriodRange(
                            periodFromField.text, periodToField.text)
                    root.close()
                }
            }
        }
    }
}
