pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var workspaceController: null

    readonly property var _resourceColumns: [
        { "key": "resource",     "label": "Resource",     "flex": 1.5, "sortable": true },
        { "key": "allocation",   "label": "Allocation",   "flex": 0.8 },
        { "key": "capacity",     "label": "Capacity",     "flex": 0.8 },
        { "key": "utilization",  "label": "Utilization",  "flex": 0.8 },
        { "key": "tasks",        "label": "Tasks",        "flex": 0,   "minWidth": 64 },
        { "key": "status",       "label": "Status",       "flex": 0.8, "type": "status" }
    ]

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Resources"
        subtitle: "Resource loading pressure, overload exposure, and utilization visibility."

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
                    id: resourcesToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.resourcesSearchText : ""
                    searchPlaceholder: "Search resources..."
                    showCustomize: true
                    showExport: true
                    showRefresh: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setResourcesSearchText(text) }
                    onCustomizeClicked: resourcesTable.openColumnCustomizer(resourcesToolbar.customizeButtonItem)
                    onExportRequested: { if (root.workspaceController !== null) root.workspaceController.exportSchedule() }
                }

                AppWidgets.DataTable {
                    id: resourcesTable
                    Layout.fillWidth: true
                    Layout.preferredHeight: 600
                    columns: root._resourceColumns
                    sourceModel: root.workspaceController ? root.workspaceController.resourcesLoadingTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.workspaceController ? (root.workspaceController.resourceLoading.emptyState || "No resource load data is available.") : "No resource load data is available."
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}
