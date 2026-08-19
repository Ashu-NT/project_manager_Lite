pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.scheduling.components 1.0

Item {
    id: root

    property var workspaceController: null

    readonly property var _proposal: root.workspaceController ? root.workspaceController.levelingProposal : ({})
    readonly property var _moveRows: root.workspaceController ? root.workspaceController.levelingMoveRows : []
    readonly property var _unresolvedConflicts: root._proposal.unresolvedConflicts || []
    readonly property var _selectedMove: {
        const rows = root._moveRows
        for (let i = 0; i < rows.length; i++) {
            if (rows[i].id === _movesTable.selectedRowId) return rows[i]
        }
        return null
    }

    readonly property var _moveColumns: [
        { "key": "taskName",       "label": "Task",      "flex": 1.6, "sortable": true },
        { "key": "shiftLabel",     "label": "Shift",     "flex": 1.6 },
        { "key": "resourcesLabel", "label": "Resources",  "flex": 1.2 },
        { "key": "statusLabel",    "label": "Status",     "flex": 0.8, "type": "status" }
    ]

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Resource Leveling"
        subtitle: "Preview resource-capacity fixes before applying them to the schedule."

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.AppTheme.spacingSm

                SchedulingActionBar {
                    Layout.fillWidth: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: [
                        { "id": "preview", "label": "Preview", "icon": "refresh", "enabled": true }
                    ]
                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if (actionId === "preview") root.workspaceController.previewResourceLeveling()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._proposal.hasPreview === true
                    spacing: Theme.AppTheme.spacingLg

                    ColumnLayout {
                        spacing: 2
                        Text { text: "Conflicts before"; color: Theme.AppTheme.textMuted }
                        Text { text: String(root._proposal.resourceConflictsBefore || 0); color: Theme.AppTheme.textPrimary; font.bold: true }
                    }
                    ColumnLayout {
                        spacing: 2
                        Text { text: "Conflicts after"; color: Theme.AppTheme.textMuted }
                        Text { text: String(root._proposal.resourceConflictsAfter || 0); color: Theme.AppTheme.textPrimary; font.bold: true }
                    }
                    ColumnLayout {
                        spacing: 2
                        Text { text: "Project finish"; color: Theme.AppTheme.textMuted }
                        Text {
                            text: (root._proposal.projectFinishBeforeLabel || "--") + " -> " + (root._proposal.projectFinishAfterLabel || "--")
                            color: Theme.AppTheme.textPrimary
                            font.bold: true
                        }
                    }
                    Item { Layout.fillWidth: true }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._unresolvedConflicts.length > 0
                    tone: "warning"
                    message: root._unresolvedConflicts.length + " resource conflict(s) could not be automatically resolved -- review below."
                }

                Repeater {
                    model: root._unresolvedConflicts
                    delegate: AppWidgets.InlineMessage {
                        required property var modelData
                        Layout.fillWidth: true
                        tone: "danger"
                        message: modelData.resourceName + " on " + modelData.conflictDateLabel
                            + " (" + modelData.totalAllocationLabel + "): " + modelData.reason
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._moveRows.length > 0

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 420

                        AppWidgets.DataTable {
                            id: _movesTable
                            anchors.fill: parent
                            columns: root._moveColumns
                            sourceModel: root.workspaceController ? root.workspaceController.levelingMovesTableModel : null
                            loading: root.workspaceController ? root.workspaceController.isLoading : false
                            emptyText: "No proposed moves."
                        }
                    }

                    AppWidgets.InspectorPanel {
                        Layout.preferredWidth: Theme.AppTheme.inspectorWidth
                        Layout.fillHeight: true
                        visible: root._selectedMove !== null
                        title: root._selectedMove ? String(root._selectedMove.taskName || "") : ""
                        statusLabel: root._selectedMove ? String(root._selectedMove.statusLabel || "") : ""
                        sections: root._selectedMove ? [
                            { "label": "WBS", "value": String(root._selectedMove.wbsCode || "--") },
                            { "label": "Old Start", "value": String(root._selectedMove.oldStartLabel || "--") },
                            { "label": "New Start", "value": String(root._selectedMove.newStartLabel || "--") },
                            { "label": "Shift", "value": root._selectedMove.shiftWorkingDays + " working day(s)" },
                            { "label": "Resources", "value": String(root._selectedMove.resourcesLabel || "--") },
                            { "label": "Reason", "value": String(root._selectedMove.reason || "") },
                            { "label": "Float", "value": String(root._selectedMove.floatBefore) + " -> " + String(root._selectedMove.floatAfter) },
                            { "label": "Deadline warning", "value": String(root._selectedMove.deadlineWarning || "None") }
                        ] : []
                        showEditAction: false
                        showSecondaryAction: false

                        onCloseRequested: _movesTable.selectedRowId = ""
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._moveRows.length > 0
                    Layout.topMargin: Theme.AppTheme.spacingSm

                    Item { Layout.fillWidth: true }

                    AppControls.PrimaryButton {
                        text: "Apply Leveling Plan"
                        iconName: "approve"
                        enabled: root.workspaceController ? !root.workspaceController.isBusy : false
                        onClicked: applyConfirmDialog.open()
                    }
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: applyConfirmDialog
        title: "Apply Resource Leveling Plan"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Apply Plan"
        confirmIcon: "approve"
        confirmDanger: false
        message: "Apply " + root._moveRows.length + " proposed move(s) to the schedule?"
        supportingText: "This writes each task's new resource-driven start date and recalculates the project schedule. It cannot be undone automatically."

        onConfirmed: {
            if (root.workspaceController) root.workspaceController.applyResourceLeveling()
        }
    }
}
