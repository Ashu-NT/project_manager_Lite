pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ".."

Item {
    id: root

    property var workspaceController: null
    property var delayedRows: []

    signal activityDetailRequested(string activityId)

    readonly property var _delayedColumns: [
        { "key": "activity", "label": "Activity", "flex": 1.7, "sortable": true },
        { "key": "finish",   "label": "Finish",   "flex": 1.0 },
        { "key": "deadline", "label": "Deadline", "flex": 1.0 },
        { "key": "delay",    "label": "Delay",    "flex": 1.0 },
        { "key": "progress", "label": "Progress", "flex": 0.9 },
        { "key": "status",   "label": "Status",   "flex": 0.8, "type": "status" }
    ]

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Delays"
        subtitle: "Delayed activities and deadline pressure requiring planner attention."

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
                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true },
                        { "id": "run_cpm", "label": "Run CPM", "icon": "approve",  "enabled": true },
                        { "id": "export",  "label": "Export",  "icon": "export",   "enabled": true }
                    ]
                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if (actionId === "refresh") root.workspaceController.refresh()
                        else if (actionId === "run_cpm") root.workspaceController.recalculateSchedule()
                        else if (actionId === "export") root.workspaceController.exportSchedule()
                    }
                }

                AppWidgets.TableToolbar {
                    id: delaysToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.delaysSearchText : ""
                    searchPlaceholder: "Search delayed activities..."
                    showCustomize: true
                    showExport: true
                    showRefresh: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setDelaysSearchText(text) }
                    onCustomizeClicked: delaysTable.openColumnCustomizer(delaysToolbar.customizeButtonItem)
                    onExportRequested: { if (root.workspaceController !== null) root.workspaceController.exportSchedule() }
                }

                AppWidgets.DataTable {
                    id: delaysTable
                    Layout.fillWidth: true
                    Layout.preferredHeight: 600
                    columns: root._delayedColumns
                    sourceModel: root.workspaceController ? root.workspaceController.delayedTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.workspaceController ? (root.workspaceController.delayedActivities.emptyState || "No delayed activities are visible.") : "No delayed activities are visible."
                    onRowActivated: function(rowId) {
                        const rows = root.delayedRows || []
                        for (let i = 0; i < rows.length; i += 1) {
                            if (String(rows[i].id || "") === String(rowId || "")) {
                                root.activityDetailRequested(rows[i].activityId || rowId)
                                return
                            }
                        }
                        root.activityDetailRequested(rowId)
                    }
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}
