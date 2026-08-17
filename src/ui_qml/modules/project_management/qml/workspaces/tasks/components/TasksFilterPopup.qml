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

    // ── Layout ───────────────────────────────────────────────────────────
    title: "Filter Tasks"
    width: 340
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

        // ── Project filter ───────────────────────────────────────────────
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
                    root.workspaceController ? root.workspaceController.selectedProjectId : ""
                )
                : 0
            onActivated: function(index) {
                const options = root.workspaceController
                    ? (root.workspaceController.projectOptions || [])
                    : []
                if (root.workspaceController !== null && options[index]) {
                    root.workspaceController.selectProject(String(options[index].value || ""))
                }
            }
        }

        // ── Status filter ────────────────────────────────────────────────
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
                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                )
                : 0
            onActivated: function(index) {
                const options = root.workspaceController
                    ? (root.workspaceController.statusOptions || [])
                    : []
                if (root.workspaceController !== null && options[index]) {
                    root.workspaceController.setStatusFilter(String(options[index].value || "all"))
                }
            }
        }

        // ── Priority filter ──────────────────────────────────────────────
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
                    root.workspaceController ? root.workspaceController.selectedPriorityFilter : "all"
                )
                : 0
            onActivated: function(index) {
                const options = root.workspaceController
                    ? (root.workspaceController.priorityOptions || [])
                    : []
                if (root.workspaceController !== null && options[index]) {
                    root.workspaceController.setPriorityFilter(String(options[index].value || "all"))
                }
            }
        }

        // ── Schedule filter ──────────────────────────────────────────────
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
                    root.workspaceController ? root.workspaceController.selectedScheduleFilter : "all"
                )
                : 0
            onActivated: function(index) {
                const options = root.workspaceController
                    ? (root.workspaceController.scheduleOptions || [])
                    : []
                if (root.workspaceController !== null && options[index]) {
                    root.workspaceController.setScheduleFilter(String(options[index].value || "all"))
                }
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
        }
    }
}
