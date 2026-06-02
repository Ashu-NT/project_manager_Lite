pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ".."

Item {
    id: root

    property var workspaceController: null

    readonly property var _diagnosticColumns: [
        { "key": "message",  "label": "Diagnostic Message", "flex": 2.0, "sortable": true },
        { "key": "severity", "label": "Severity",           "flex": 0.9, "type": "status" },
        { "key": "metric",   "label": "Scope",              "flex": 1.1 },
        { "key": "status",   "label": "Value",              "flex": 0.9 },
        { "key": "details",  "label": "Details",            "flex": 1.8 }
    ]
    readonly property var _violationColumns: [
        { "key": "activity",       "label": "Activity",        "flex": 1.5, "sortable": true },
        { "key": "constraintType", "label": "Constraint",      "flex": 1.3 },
        { "key": "required",       "label": "Required Date",   "flex": 0.9 },
        { "key": "computed",       "label": "Computed Date",   "flex": 0.9 },
        { "key": "overrunDays",    "label": "Overrun (days)",  "flex": 0,   "minWidth": 110 },
        { "key": "severity",       "label": "Severity",        "flex": 0.9, "type": "status" }
    ]

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Diagnostics"
        subtitle: "Planner-quality checks for network logic, float pressure, and schedule stability."

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
                        { "id": "refresh", "label": "Refresh Diagnostics", "icon": "refresh", "enabled": true },
                        { "id": "run_cpm", "label": "Run CPM",             "icon": "approve",  "enabled": true },
                        { "id": "export",  "label": "Export Report",       "icon": "export",   "enabled": true }
                    ]
                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if (actionId === "refresh") root.workspaceController.refresh()
                        else if (actionId === "run_cpm") root.workspaceController.recalculateSchedule()
                        else if (actionId === "export") root.workspaceController.exportSchedule()
                    }
                }

                AppWidgets.TableToolbar {
                    id: diagnosticsToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.diagnosticsSearchText : ""
                    searchPlaceholder: "Search diagnostics..."
                    showCustomize: true
                    showExport: true
                    showRefresh: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setDiagnosticsSearchText(text) }
                    onCustomizeClicked: diagnosticsTable.openColumnCustomizer(diagnosticsToolbar.customizeButtonItem)
                    onExportRequested: { if (root.workspaceController !== null) root.workspaceController.exportSchedule() }
                }

                AppWidgets.DataTable {
                    id: diagnosticsTable
                    Layout.fillWidth: true
                    Layout.preferredHeight: 320
                    columns: root._diagnosticColumns
                    sourceModel: root.workspaceController ? root.workspaceController.diagnosticsTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.workspaceController ? (root.workspaceController.diagnostics.emptyState || "No diagnostics are available.") : "No diagnostics are available."
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Constraint Violations"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 480
                    columns: root._violationColumns
                    sourceModel: root.workspaceController ? root.workspaceController.violationsTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.workspaceController ? (root.workspaceController.constraintViolations.emptyState || "No constraint violations detected.") : "No constraint violations detected."
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}
