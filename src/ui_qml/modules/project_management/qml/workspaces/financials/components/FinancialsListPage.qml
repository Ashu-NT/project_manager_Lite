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
    property var overviewModel: ({ "metrics": [] })
    property var costsModel: ({ "emptyState": "No cost items available." })
    property var columns: []
    property string tableId: "pm.financials.costs.table"
    property var bulkChangeProperties: []

    signal rowActivated(string rowId)
    signal columnsStateChanged(var cols)
    signal createRequested()

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

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
            message: "Loading financials..."
            compact: true; modal: false
        }
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController
                ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                : false
            message: "Saving changes..."
            compact: true; modal: false
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
            searchPlaceholder: "Search cost items..."
            showCreate: true
            createEnabled: root.workspaceController ? root.workspaceController.selectedProjectId.length > 0 : false
            createLabel: "Add Cost"
            showFilter: true
            showCustomize: true
            showViews: true
            showRefresh: true
            showExport: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked: filterPopup.open()
            onCustomizeClicked: costsTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            onViewsClicked: viewsPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onExportRequested: { if (root.workspaceController !== null) root.workspaceController.exportFinancials() }
            onCreateRequested: root.createRequested()
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: costsTable
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                multiSelect: true
                tableId: root.tableId
                columns: root.columns
                sourceModel: root.workspaceController ? root.workspaceController.costsTableModel : null
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.costsModel.emptyState || "No cost items available."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedCostId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedCostIds || []) : []
                onColumnsStateChanged: function(cols) { root.columnsStateChanged(cols) }
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectCost(rowId) }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                    root.rowActivated(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                    root.rowActivated(rowId)
                }
                onRowSelectionToggled: function(rowId, selected) { if (root.workspaceController !== null) root.workspaceController.setCostBulkSelection(rowId, selected) }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleCosts()
                    else root.workspaceController.clearCostBulkSelection()
                }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.costPage : 1
                pageSize: root.workspaceController ? root.workspaceController.costPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.costTotalCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                onPageRequested: function(page) { if (root.workspaceController !== null) root.workspaceController.setCostPage(page) }
                onPageSizeRequested: function(pageSize) { if (root.workspaceController !== null) root.workspaceController.setCostPageSize(pageSize) }
            }

            AppWidgets.BulkActionBar {
                id: _bulkActionBar
                anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: _paginationBar.top; anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedCostCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { "id": "delete",          "label": "Delete",          "icon": "delete", "danger": true,  "enabled": true },
                    { "id": "change_property", "label": "Change Cost Type","icon": "edit",   "danger": false, "enabled": true }
                ]
                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearCostBulkSelection() }
                onActionTriggered: function(actionId) {
                    if (actionId === "delete") {
                        root.workspaceController.bulkDeleteCosts(root.workspaceController ? (root.workspaceController.selectedCostIds || []) : [])
                    } else if (actionId === "change_property") {
                        _bulkChangePropertyPopup.open()
                    }
                }
            }

            AppWidgets.BulkChangePropertyPopup {
                id: _bulkChangePropertyPopup
                anchorItem: _bulkActionBar.actionButtonForId("change_property")
                selectedCount: root.workspaceController ? root.workspaceController.selectedCostCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                properties: root.bulkChangeProperties
                onApplyRequested: function(payload) {
                    if (root.workspaceController === null) return
                    if (payload.propertyId === "costType") root.workspaceController.applyBulkCostType({ "value": payload.value })
                }
            }

            // ── Filter popup ──────────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem
                width: 280; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Project"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(root.workspaceController ? (root.workspaceController.projectOptions || []) : [], root.workspaceController ? root.workspaceController.selectedProjectId : "")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.selectProject(String(opts[index].value || ""))
                        }
                    }

                    AppControls.Label { text: "Cost Type"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(root.workspaceController ? (root.workspaceController.costTypeOptions || []) : [], root.workspaceController ? root.workspaceController.selectedCostType : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.setCostTypeFilter(String(opts[index].value || "all"))
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.AppTheme.spacingSm
                        AppControls.SecondaryButton { Layout.fillWidth: true; text: "Clear"; iconName: "close"; onClicked: { if (root.workspaceController !== null) { root.workspaceController.selectProject(""); root.workspaceController.setCostTypeFilter("all") }; filterPopup.close() } }
                        AppControls.SecondaryButton { Layout.fillWidth: true; text: "Close"; iconName: "close"; onClicked: filterPopup.close() }
                    }
                }
            }

            // ── Views popup ───────────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: viewsPopup
                anchorItem: tableToolbar.viewsButtonItem
                width: 260; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm
                    AppControls.Label { text: "Cost View"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(root.workspaceController ? (root.workspaceController.costTypeOptions || []) : [], root.workspaceController ? root.workspaceController.selectedCostType : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) { root.workspaceController.setCostTypeFilter(String(opts[index].value || "all")); viewsPopup.close() }
                        }
                    }
                }
            }
        }
    }
}
