pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController
    property var heatmapModel: ({ "emptyState": "No heatmap rows are available yet.", "items": [] })
    property var heatmapColumns: []
    property string selectedRowId: ""

    signal rowActivated(string rowId)

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.heatmapSearchText : ""
            searchPlaceholder: "Search projects by name..."
            showRefresh: true
            showExport: false
            showFilter: false
            showCreate: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setHeatmapSearchText(text)
            }
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: _heatmapTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: _paginationBar.top
                multiSelect: false
                columns: root.heatmapColumns
                sourceModel: root.workspaceController ? root.workspaceController.heatmapTableModel : null
                sortingMode: "none"
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.heatmapModel.emptyState || "No portfolio projects available."
                selectedRowId: root.selectedRowId

                onRowSelected: function(rowId) { root.selectedRowId = rowId }
                onRowActivated: function(rowId) {
                    root.selectedRowId = rowId
                    root.rowActivated(rowId)
                }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.heatmapPage : 1
                pageSize: root.workspaceController ? root.workspaceController.heatmapPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.heatmapTotalCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                onPageRequested: function(page) {
                    if (root.workspaceController !== null) root.workspaceController.setHeatmapPage(page)
                }
                onPageSizeRequested: function(ps) {
                    if (root.workspaceController !== null) root.workspaceController.setHeatmapPageSize(ps)
                }
            }
        }
    }
}
