pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Item {
    id: root

    property var workspaceController: null
    property var state: null
    property var overviewModel: ({})
    property var projectsModel: ({})
    property var selectedProjectModel: ({})

    readonly property var bulkActionBar: bulkActionBarItem
    readonly property var customizeButtonItem: tableToolbar.customizeButtonItem

    function _optionLabelForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return String(list[i].label || value)
        }
        return String(value || "")
    }

    // Concise active-filter chips shown beneath the toolbar so the applied
    // filter state stays visible without consuming permanent toolbar width
    // (the filter surface itself lives in the modal ProjectsFilterPopup).
    readonly property var _activeFilterChips: {
        const c = root.workspaceController
        if (!c) return []
        const chips = []
        if (c.selectedStatusFilter && c.selectedStatusFilter !== "all") {
            chips.push({ "key": "status", "label": "Status: " + root._optionLabelForValue(c.statusOptions, c.selectedStatusFilter) })
        }
        if (c.projectNameFilter) {
            chips.push({ "key": "projectName", "label": "Project: " + c.projectNameFilter })
        }
        if (c.clientNameFilter) {
            chips.push({ "key": "clientName", "label": "Client: " + c.clientNameFilter })
        }
        if (c.selectedSiteFilter && c.selectedSiteFilter !== "all") {
            chips.push({ "key": "site", "label": "Site: " + root._optionLabelForValue(c.siteOptions, c.selectedSiteFilter) })
        }
        if (c.selectedDepartmentFilter && c.selectedDepartmentFilter !== "all") {
            chips.push({ "key": "department", "label": "Department: " + root._optionLabelForValue(c.departmentOptions, c.selectedDepartmentFilter) })
        }
        if (c.selectedManagerFilter && c.selectedManagerFilter !== "all") {
            chips.push({ "key": "manager", "label": "Manager: " + root._optionLabelForValue(c.managerOptions, c.selectedManagerFilter) })
        }
        if (c.startDateFrom || c.startDateTo) {
            chips.push({ "key": "startRange", "label": "Start: " + (c.startDateFrom || "…") + " to " + (c.startDateTo || "…") })
        }
        if (c.endDateFrom || c.endDateTo) {
            chips.push({ "key": "endRange", "label": "Finish: " + (c.endDateFrom || "…") + " to " + (c.endDateTo || "…") })
        }
        return chips
    }

    function _clearFilterChip(key) {
        const c = root.workspaceController
        if (!c) return
        if (key === "status") c.setStatusFilter("all")
        else if (key === "projectName") c.setProjectNameFilter("")
        else if (key === "clientName") c.setClientNameFilter("")
        else if (key === "site") c.setSiteFilter("all")
        else if (key === "department") c.setDepartmentFilter("all")
        else if (key === "manager") c.setManagerFilter("all")
        else if (key === "startRange") { c.setStartDateFrom(""); c.setStartDateTo("") }
        else if (key === "endRange") { c.setEndDateFrom(""); c.setEndDateTo("") }
    }

    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal rowSelectionToggled(string rowId, bool selected)
    signal selectAllToggled(bool allSelected)
    signal columnsStateChanged(var columns)
    signal searchChanged(string text)
    signal filterClicked()
    signal refreshRequested()
    signal importRequested()
    signal exportRequested()
    signal createRequested()
    signal bulkCancelRequested()
    signal bulkActionRequested(string actionId)

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
            message: "Loading projects..."
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
            searchPlaceholder: "Search projects..."
            showCreate: true
            createLabel: "New Project"
            showFilter: true
            showCustomize: true
            showRefresh: true
            showImport: true
            showExport: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) { root.searchChanged(text) }
            onFilterClicked: root.filterClicked()
            onCustomizeClicked: projectsTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            onRefreshRequested: root.refreshRequested()
            onImportRequested: root.importRequested()
            onExportRequested: root.exportRequested()
            onCreateRequested: root.createRequested()
        }

        Flow {
            Layout.fillWidth: true
            visible: root._activeFilterChips.length > 0
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: root._activeFilterChips

                delegate: Rectangle {
                    id: chipRoot
                    required property var modelData

                    implicitHeight: 24
                    implicitWidth: chipRow.implicitWidth + Theme.AppTheme.spacingSm * 2
                    radius: implicitHeight / 2
                    color: Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.borderStrong
                    border.width: 1

                    RowLayout {
                        id: chipRow
                        anchors.centerIn: parent
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            text: chipRoot.modelData.label
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }

                        Item {
                            implicitWidth: 14
                            implicitHeight: 14

                            AppIcons.AppIcon {
                                anchors.centerIn: parent
                                name: "close"
                                size: Theme.AppTheme.iconXs
                                iconColor: Theme.AppTheme.textMuted
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root._clearFilterChip(chipRoot.modelData.key)
                            }
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: projectsTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: paginationBar.top
                multiSelect: true
                tableId: root.state ? root.state.tableId : ""
                columns: root.state ? root.state.columns : []
                sourceModel: root.workspaceController ? root.workspaceController.projectsTableModel : null
                sortingMode: "server"
                sortKey: root.workspaceController ? root.workspaceController.projectSortKey : "title"
                sortDirection: root.workspaceController
                    ? root.workspaceController.projectSortDirection
                    : Qt.AscendingOrder
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.projectsModel.emptyState || "No projects available."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedProjectIds || []) : []

                onRowSelected: function(rowId) { root.rowSelected(rowId) }
                onRowActivated: function(rowId) { root.rowActivated(rowId) }
                onViewDetailRequested: function(rowId) { root.rowActivated(rowId) }
                onRowSelectionToggled: function(rowId, selected) { root.rowSelectionToggled(rowId, selected) }
                onSelectAllToggled: function(allSelected) { root.selectAllToggled(allSelected) }
                onColumnsStateChanged: function(columns) { root.columnsStateChanged(columns) }
                onSortRequested: function(key, direction) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setProjectSort(key, direction)
                }
            }

            AppWidgets.TablePaginationBar {
                id: paginationBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.projectPage : 1
                pageSize: root.workspaceController ? root.workspaceController.projectPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.projectTotalCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false

                onPageRequested: function(page) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setProjectPage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setProjectPageSize(pageSize)
                }
            }

            AppWidgets.BulkActionBar {
                id: bulkActionBarItem
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedProjectCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true },
                    { "id": "change_property", "label": "Change Property", "icon": "edit", "danger": false, "enabled": true }
                ]

                onCancelRequested: root.bulkCancelRequested()
                onActionTriggered: function(actionId) {
                    root.bulkActionRequested(actionId)
                }
            }
        }
    }
}
