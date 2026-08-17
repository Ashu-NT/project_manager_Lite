pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var workspaceController: null
    property var state: null

    title: "Filter Review Queue"
    width: 360
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            text: "Status"
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
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.setQueueStatus(String(opts[index].value || "SUBMITTED"))
            }
        }

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
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Clear"
                iconName: "refresh"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setQueueProject("all")
                        root.workspaceController.setQueueResource("all")
                        root.workspaceController.setQueuePeriodRange("", "")
                    }
                    root.close()
                }
            }
            Item { Layout.fillWidth: true }
            AppControls.PrimaryButton {
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
