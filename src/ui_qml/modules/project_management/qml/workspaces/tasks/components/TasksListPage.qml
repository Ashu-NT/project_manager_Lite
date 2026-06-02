pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var workspaceController: null
    property var state: null
    property var overviewModel: ({})
    property var tasksModel: ({})
    property var tasksTableModel: null
    property var selectedTaskModel: ({})

    // ── Exposed UI elements for popup anchoring ────────────────────────
    readonly property var filterButtonItem: tableToolbar.filterButtonItem
    readonly property var viewsButtonItem: tableToolbar.viewsButtonItem

    // ── Signals ──────────────────────────────────────────────────────────
    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal columnsStateChanged(var columns)
    signal searchChanged(string text)
    signal filterClicked()
    signal customizeClicked()
    signal viewsClicked()
    signal refreshRequested()
    signal exportRequested()
    signal createRequested()

    // ── Layout ───────────────────────────────────────────────────────────
    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        // ── KPI Strip ────────────────────────────────────────────────────
        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        // ── Loading overlay (initial load) ──────────────────────────────
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && !(root.workspaceController ? root.workspaceController.isBusy : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading tasks..."
            compact: true
            modal:   false
        }

        // ── Loading overlay (save) ───────────────────────────────────────
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController
                ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                : false
            message: "Saving task changes..."
            compact: true
            modal:   false
        }

        // ── Error message ────────────────────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        // ── Success message ──────────────────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        // ── Table toolbar ────────────────────────────────────────────────
        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: "Search tasks..."
            showCreate: true
            createEnabled: root.workspaceController
                ? (root.workspaceController.projectOptions || []).some(function(option) {
                    return String(option.value || "").toLowerCase() !== "all"
                })
                : false
            createLabel: "New Task"
            showFilter: true
            showCustomize: true
            showViews: true
            showRefresh: true
            showExport: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                root.searchChanged(text)
            }
            onFilterClicked: root.filterClicked()
            onCustomizeClicked: tasksTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            onViewsClicked: root.viewsClicked()
            onRefreshRequested: root.refreshRequested()
            onExportRequested: root.exportRequested()
            onCreateRequested: root.createRequested()
        }

        // ── Table + pagination container ─────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            // ── Data table ───────────────────────────────────────────────
            AppWidgets.DataTable {
                id: tasksTable
                anchors.top:    parent.top
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: paginationBar.top
                multiSelect: true
                tableId: root.state ? root.state.tableId : ""
                columns: root.state ? root.state.columns : []
                sourceModel: root.tasksTableModel
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.tasksModel.emptyState || "No tasks available."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []

                onRowSelected: function(rowId) {
                    root.rowSelected(rowId)
                }
                onRowActivated: function(rowId) {
                    root.rowActivated(rowId)
                }
                onRowSelectionToggled: function(rowId, selected) {
                    root.rowSelectionToggled(rowId, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    root.selectAllToggled(allSelected)
                }
                onColumnsStateChanged: function(columns) {
                    root.columnsStateChanged(columns)
                }
            }

            // ── Pagination bar ───────────────────────────────────────────
            AppWidgets.TablePaginationBar {
                id: paginationBar
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: parent.bottom
                currentPage:  root.workspaceController ? root.workspaceController.taskPage     : 1
                pageSize:     root.workspaceController ? root.workspaceController.taskPageSize  : 25
                totalItems:   root.workspaceController ? root.workspaceController.taskTotalCount : 0
                busy:         root.workspaceController ? root.workspaceController.isBusy        : false

                onPageRequested: function(page) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setTaskPage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setTaskPageSize(pageSize)
                }
            }
        }
    }
}
