pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController
    property var shellModel: null

    readonly property var operationalTabsModel: root.workspaceController
        ? (root.workspaceController.operationalTabs || [])
        : []
    readonly property var operationalTableModel: root.workspaceController
        ? (root.workspaceController.operationalTable || {})
        : ({ "title": "", "subtitle": "", "emptyState": "No operational data is available yet.", "columns": [], "rows": [] })
    readonly property var operationalSourceModel: root.workspaceController
        ? root.workspaceController.operationalTableModel
        : null
    readonly property var activityFeedModel: root.workspaceController
        ? (root.workspaceController.activityFeed || {})
        : ({ "title": "Recent Activity", "subtitle": "", "emptyState": "No recent activity is available yet.", "items": [] })
    readonly property bool splitLayout: width >= 1360

    function tabsForBar() {
        const tabs = root.operationalTabsModel || []
        const values = []
        for (let index = 0; index < tabs.length; index += 1) {
            const tab = tabs[index] || {}
            const count = Number(tab.count || 0)
            values.push({
                "id": String(tab.id || ""),
                "label": count > 0
                    ? String(tab.label || "") + " (" + count + ")"
                    : String(tab.label || "")
            })
        }
        return values
    }

    function selectedTabIndex() {
        const tabs = root.operationalTabsModel || []
        const selectedId = root.workspaceController ? root.workspaceController.selectedOperationalTabId : ""
        for (let index = 0; index < tabs.length; index += 1) {
            if (String((tabs[index] || {}).id || "") === String(selectedId || "")) {
                return index
            }
        }
        return 0
    }

    function findOperationalRow(rowId) {
        const rows = root.operationalTableModel.rows || []
        for (let index = 0; index < rows.length; index += 1) {
            const row = rows[index] || {}
            if (String(row.id || "") === String(rowId || "")) {
                return row
            }
        }
        return null
    }

    function activateOperationalRoute(rowId) {
        const row = root.findOperationalRow(rowId)
        if (!row || !root.shellModel) {
            return
        }
        const routeId = String(row.routeId || "")
        if (routeId.length > 0) {
            root.shellModel.selectRoute(routeId)
        }
    }

    implicitHeight: contentLayout.implicitHeight

    ColumnLayout {
        id: contentLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingSm
            visible: root.splitLayout

            DashboardPanelFrame {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Operational Views"
                subtitle: "Executive drill-down into delayed tasks, risks, budget pressure, resource load, approvals, and milestones."

                DashboardOperationalPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    workspaceController: root.workspaceController
                    operationalTabsModel: root.operationalTabsModel
                    operationalTableModel: root.operationalTableModel
                    operationalSourceModel: root.operationalSourceModel
                    onOperationalRouteRequested: function(routeId) {
                        if (root.shellModel && String(routeId || "").length > 0) {
                            root.shellModel.selectRoute(routeId)
                        }
                    }
                }
            }

            DashboardPanelFrame {
                Layout.preferredWidth: 360
                Layout.fillHeight: true
                title: root.activityFeedModel.title || "Recent Activity"
                subtitle: root.activityFeedModel.subtitle || "Workflow updates, approvals, and project events."

                AppWidgets.ActivityFeed {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    items: root.activityFeedModel.items || []
                    emptyText: root.activityFeedModel.emptyState || "No recent activity is available yet."

                    onItemActivated: function(item) {
                        if (!root.shellModel) {
                            return
                        }
                        const routeId = String(item.routeId || "")
                        if (routeId.length > 0) {
                            root.shellModel.selectRoute(routeId)
                        }
                    }
                }
            }
        }

        DashboardPanelFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 420
            Layout.minimumHeight: 260
            visible: !root.splitLayout
            title: "Operational Views"
            subtitle: "Executive drill-down into delayed tasks, risks, budget pressure, resource load, approvals, and milestones."

            DashboardOperationalPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                workspaceController: root.workspaceController
                operationalTabsModel: root.operationalTabsModel
                operationalTableModel: root.operationalTableModel
                operationalSourceModel: root.operationalSourceModel
                onOperationalRouteRequested: function(routeId) {
                    if (root.shellModel && String(routeId || "").length > 0) {
                        root.shellModel.selectRoute(routeId)
                    }
                }
            }
        }

        DashboardPanelFrame {
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            Layout.minimumHeight: 160
            visible: !root.splitLayout
            title: root.activityFeedModel.title || "Recent Activity"
            subtitle: root.activityFeedModel.subtitle || "Workflow updates, approvals, and project events."

            AppWidgets.ActivityFeed {
                Layout.fillWidth: true
                Layout.fillHeight: true
                items: root.activityFeedModel.items || []
                emptyText: root.activityFeedModel.emptyState || "No recent activity is available yet."

                onItemActivated: function(item) {
                    if (!root.shellModel) {
                        return
                    }
                    const routeId = String(item.routeId || "")
                    if (routeId.length > 0) {
                        root.shellModel.selectRoute(routeId)
                    }
                }
            }
        }
    }
}

