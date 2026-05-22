pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController
    property var operationalTabsModel: []
    property var operationalTableModel: ({ "title": "", "subtitle": "", "emptyState": "", "columns": [], "rows": [] })

    signal operationalRouteRequested(string routeId)

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
        if (!row) {
            return
        }
        const routeId = String(row.routeId || "")
        if (routeId.length > 0) {
            root.operationalRouteRequested(routeId)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.DetailTabBar {
            Layout.fillWidth: true
            tabs: root.tabsForBar()
            currentIndex: root.selectedTabIndex()
            visible: (root.operationalTabsModel || []).length > 0

            onTabSelected: function(index) {
                const tabs = root.operationalTabsModel || []
                const tab = tabs[index]
                if (root.workspaceController !== null && tab) {
                    root.workspaceController.selectOperationalTab(String(tab.id || ""))
                }
            }
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.operationalSearchText : ""
            searchPlaceholder: "Search " + String(root.operationalTableModel.title || "rows").toLowerCase() + "..."
            showRefresh: false
            showExport: false
            showCreate: false
            showFilter: false
            showViews: false
            showCustomize: true
            isBusy: root.workspaceController
                ? (root.workspaceController.isBusy || root.workspaceController.isLoading)
                : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) {
                    root.workspaceController.setOperationalSearchText(text)
                }
            }
            onCustomizeClicked: operationalTable.openColumnCustomizer()
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: operationalTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: paginationBar.top
                columns: root.operationalTableModel.columns || []
                rows: root.operationalTableModel.rows || []
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.operationalTableModel.emptyState || "No operational records are available."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedOperationalRowId : ""
                multiSelect: false

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectOperationalRow(rowId)
                    }
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectOperationalRow(rowId)
                    }
                    root.activateOperationalRoute(rowId)
                }
                onSortRequested: function(key) {}
            }

            AppWidgets.TablePaginationBar {
                id: paginationBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.operationalPage : 1
                pageSize: root.workspaceController ? root.workspaceController.operationalPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.operationalTotalCount : 0
                busy: root.workspaceController
                    ? (root.workspaceController.isBusy || root.workspaceController.isLoading)
                    : false

                onPageRequested: function(page) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setOperationalPage(page)
                    }
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setOperationalPageSize(pageSize)
                    }
                }
            }
        }
    }
}
