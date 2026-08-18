pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var workspaceController: null
    property var state: null

    // Draft selections, staged until Apply commits them to the controller.
    property string _draftProjectId: ""
    property string _draftStatus: "all"
    property string _draftPriority: "all"
    property string _draftSchedule: "all"

    // ── Layout ───────────────────────────────────────────────────────────
    title: "Filter Tasks"
    width: 360
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    onAboutToShow: {
        root._draftProjectId = root.workspaceController ? root.workspaceController.selectedProjectId : ""
        root._draftStatus = root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
        root._draftPriority = root.workspaceController ? root.workspaceController.selectedPriorityFilter : "all"
        root._draftSchedule = root.workspaceController ? root.workspaceController.selectedScheduleFilter : "all"
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            spacing: Theme.AppTheme.spacingSm

            // ── Project filter ───────────────────────────────────────────
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
                        root._draftProjectId
                    )
                    : 0
                onActivated: function(index) {
                    const options = root.workspaceController
                        ? (root.workspaceController.projectOptions || [])
                        : []
                    if (options[index])
                        root._draftProjectId = String(options[index].value || "")
                }
            }

            // ── Status filter ────────────────────────────────────────────
            AppControls.Label {
                text: "Status"
                font.bold: true
                font.pixelSize: Theme.AppTheme.captionSize
                font.family: Theme.AppTheme.fontFamily
                color: Theme.AppTheme.textMuted
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                textRole: "label"
                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                currentIndex: root.state
                    ? root.state.optionIndexForValue(
                        root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                        root._draftStatus
                    )
                    : 0
                onActivated: function(index) {
                    const options = root.workspaceController
                        ? (root.workspaceController.statusOptions || [])
                        : []
                    if (options[index])
                        root._draftStatus = String(options[index].value || "all")
                }
            }

            // ── Priority filter ──────────────────────────────────────────
            AppControls.Label {
                text: "Priority"
                font.bold: true
                font.pixelSize: Theme.AppTheme.captionSize
                font.family: Theme.AppTheme.fontFamily
                color: Theme.AppTheme.textMuted
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                textRole: "label"
                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                currentIndex: root.state
                    ? root.state.optionIndexForValue(
                        root.workspaceController ? (root.workspaceController.priorityOptions || []) : [],
                        root._draftPriority
                    )
                    : 0
                onActivated: function(index) {
                    const options = root.workspaceController
                        ? (root.workspaceController.priorityOptions || [])
                        : []
                    if (options[index])
                        root._draftPriority = String(options[index].value || "all")
                }
            }

            // ── Schedule filter ───────────────────────────────────────────
            AppControls.Label {
                text: "Schedule"
                font.bold: true
                font.pixelSize: Theme.AppTheme.captionSize
                font.family: Theme.AppTheme.fontFamily
                color: Theme.AppTheme.textMuted
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.workspaceController ? (root.workspaceController.scheduleOptions || []) : []
                textRole: "label"
                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                currentIndex: root.state
                    ? root.state.optionIndexForValue(
                        root.workspaceController ? (root.workspaceController.scheduleOptions || []) : [],
                        root._draftSchedule
                    )
                    : 0
                onActivated: function(index) {
                    const options = root.workspaceController
                        ? (root.workspaceController.scheduleOptions || [])
                        : []
                    if (options[index])
                        root._draftSchedule = String(options[index].value || "all")
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        // ── Action buttons ───────────────────────────────────────────────
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
                        root.workspaceController.clearFilters()
                    }
                    root.close()
                }
            }

            Item { Layout.fillWidth: true }

            AppControls.SecondaryButton {
                text: "Close"
                iconName: "close"
                onClicked: root.close()
            }

            AppControls.PrimaryButton {
                text: "Apply"
                iconName: "approve"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(root._draftProjectId)
                        root.workspaceController.setStatusFilter(root._draftStatus)
                        root.workspaceController.setPriorityFilter(root._draftPriority)
                        root.workspaceController.setScheduleFilter(root._draftSchedule)
                    }
                    root.close()
                }
            }
        }
    }
}
