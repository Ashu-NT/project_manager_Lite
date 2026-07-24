pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property var state: null
    property var overviewModel: ({})
    property var resourcesModel: ({})

    readonly property var bulkActionBar: bulkActionBarItem
    readonly property var filterButtonItem: tableToolbar.filterButtonItem
    readonly property var customizeButtonItem: tableToolbar.customizeButtonItem

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal columnsStateChanged(var columns)
    signal searchChanged(string text)
    signal filterClicked()
    signal refreshRequested()
    signal exportRequested()
    signal createRequested()
    signal bulkCancelRequested()
    signal bulkActionRequested(string actionId)

    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && !(root.workspaceController ? root.workspaceController.isBusy : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading resources..."
            compact: true
            modal: false
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController
                ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                : false
            message: "Saving changes..."
            compact: true
            modal: false
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: "Search resources..."
            showCreate: true
            createLabel: "New Resource"
            showFilter: true
            showCustomize: true
            showRefresh: true
            showExport: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) { root.searchChanged(text) }
            onFilterClicked: root.filterClicked()
            onCustomizeClicked: resourcesTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            onRefreshRequested: root.refreshRequested()
            onExportRequested: root.exportRequested()
            onCreateRequested: root.createRequested()
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: resourcesTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: paginationBar.top
                multiSelect: true
                tableId: root.state ? root.state.tableId : ""
                columns: root.state ? root.state.columns : []
                sourceModel: root.workspaceController ? root.workspaceController.resourcesTableModel : null
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.resourcesModel.emptyState || "No resources available."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedResourceId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedResourceIds || []) : []

                onRowSelected: function(rowId) { root.rowSelected(rowId) }
                onRowActivated: function(rowId) { root.rowActivated(rowId) }
                onViewDetailRequested: function(rowId) { root.rowActivated(rowId) }
                onRowSelectionToggled: function(rowId, selected) { root.rowSelectionToggled(rowId, selected) }
                onSelectAllToggled: function(allSelected) { root.selectAllToggled(allSelected) }
                onColumnsStateChanged: function(columns) { root.columnsStateChanged(columns) }
            }

            AppWidgets.TablePaginationBar {
                id: paginationBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.resourcePage : 1
                pageSize: root.workspaceController ? root.workspaceController.resourcePageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.resourceTotalCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false

                onPageRequested: function(page) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setResourcePage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setResourcePageSize(pageSize)
                }
            }

            AppWidgets.BulkActionBar {
                id: bulkActionBarItem
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedResourceCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true }
                ]

                onCancelRequested: root.bulkCancelRequested()
                onActionTriggered: function(actionId) {
                    root.bulkActionRequested(actionId)
                }
            }
        }
    }
}
