pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementRegisterWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.registerWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.register",
            "title": "Register",
            "summary": "Controlled project register records and governance-facing project history."
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var entriesModel: root.workspaceController
        ? root.workspaceController.entries
        : ({
            "title": "Project Register",
            "subtitle": "Track risks, issues, and changes across the selected project scope.",
            "emptyState": "Select a project to review register entries.",
            "items": []
        })
    readonly property var selectedEntryModel: root.workspaceController
        ? root.workspaceController.selectedEntry
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a register entry to review governance details.",
            "fields": [],
            "state": {}
        })
    readonly property var urgentModel: root.workspaceController
        ? root.workspaceController.urgentEntries
        : ({
            "title": "Urgent Review Queue",
            "subtitle": "Severity-first shortlist to help triage what needs attention next.",
            "emptyState": "No urgent register items.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _tableColumns: [
        { "key": "title",        "label": "Issue",    "flex": 2,   "sortable": true  },
        { "key": "statusLabel",  "label": "Severity", "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "typeLabel",    "label": "Type",     "flex": 0,   "minWidth": 90,  "type": "status" },
        { "key": "projectName",  "label": "Project",  "flex": 1.5, "sortable": true  },
        { "key": "ownerName",    "label": "Owner",    "flex": 1.5                    },
        { "key": "dueDateLabel", "label": "Due",      "flex": 0,   "minWidth": 90    }
    ]

    readonly property var _detailActions: [
        { "id": "edit",   "label": "Edit",   "icon": "edit",   "enabled": true, "danger": false },
        { "id": "delete", "label": "Delete", "icon": "delete", "enabled": true, "danger": true  }
    ]

    readonly property var _bulkChangeProperties: {
        const props = []
        const statusOpts = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || [])
            : []
        if (statusOpts.length > 0) {
            props.push({ "id": "status", "label": "Status", "values": statusOpts })
        }
        return props
    }

    function _optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    ProjectManagementWidgets.RegisterDialogHost {
        id: dialogHost

        projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
        typeOptions: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        severityOptions: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
        typeFieldVisible: true
        fixedTypeValue: "RISK"
        entryLabel: "Register Entry"

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createEntry(payload)
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateEntry(payload)
        }
        onDeleteRequested: function(entryId) {
            if (root.workspaceController !== null) root.workspaceController.deleteEntry(entryId)
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────────
    Item {
        anchors.fill: parent

        // ── List page (hidden when detail is open) ────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !detailPage.open

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading register..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Saving changes..."
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
                    searchPlaceholder: "Search register entries..."
                    showCreate: true
                    createLabel: "New Entry"
                    showFilter: true
                    showCustomize: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: registerTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {}
                    onCreateRequested: dialogHost.openCreateDialog()
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: registerTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._tableColumns
                        rows: root.entriesModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.entriesModel.emptyState || "No register entries available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedEntryIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                            detailPage.open = true
                        }
                        onViewDetailRequested: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                            detailPage.open = true
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setEntryBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleEntries()
                            else root.workspaceController.clearEntryBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.entryPage       : 1
                        pageSize:     root.workspaceController ? root.workspaceController.entryPageSize    : 25
                        totalItems:   root.workspaceController ? root.workspaceController.entryTotalCount  : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy           : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setEntryPage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null) root.workspaceController.setEntryPageSize(pageSize)
                        }
                    }

                    AppWidgets.BulkActionBar {
                        id: _bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedEntryCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "delete",          "label": "Delete",         "icon": "delete", "danger": true,  "enabled": true },
                            { "id": "change_property", "label": "Change Status",  "icon": "edit",   "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearEntryBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (root.workspaceController === null) return
                            if (actionId === "delete") {
                                root.workspaceController.bulkDeleteEntries(
                                    root.workspaceController.selectedEntryIds || []
                                )
                            } else if (actionId === "change_property") {
                                _bulkChangePropertyPopup.open()
                            }
                        }
                    }

                    AppWidgets.BulkChangePropertyPopup {
                        id: _bulkChangePropertyPopup
                        anchorItem: _bulkActionBar.actionButtonForId("change_property")
                        selectedCount: root.workspaceController ? root.workspaceController.selectedEntryCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        properties: root._bulkChangeProperties

                        onApplyRequested: function(payload) {
                            if (root.workspaceController === null) return
                            if (payload.propertyId === "status")
                                root.workspaceController.applyBulkEntryStatus({ "value": payload.value })
                        }
                    }

                    // ── Filter popup ──────────────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem: tableToolbar.filterButtonItem
                        width: 280
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            Label {
                                text: "Project"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedProjectId : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.selectProject(String(opts[index].value || "all"))
                                }
                            }

                            Label {
                                text: "Type"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.typeOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedTypeFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.setTypeFilter(String(opts[index].value || "all"))
                                }
                            }

                            Label {
                                text: "Status"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.setStatusFilter(String(opts[index].value || "all"))
                                }
                            }

                            Label {
                                text: "Severity"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.severityOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedSeverityFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.setSeverityFilter(String(opts[index].value || "all"))
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Clear"
                                    iconName: "close"
                                    onClicked: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.selectProject("all")
                                            root.workspaceController.setTypeFilter("all")
                                            root.workspaceController.setStatusFilter("all")
                                            root.workspaceController.setSeverityFilter("all")
                                        }
                                        filterPopup.close()
                                    }
                                }
                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Close"
                                    iconName: "close"
                                    onClicked: filterPopup.close()
                                }
                            }
                        }
                    }

                    // ── Views popup ───────────────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: viewsPopup
                        anchorItem: tableToolbar.viewsButtonItem
                        width: 260
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            Label {
                                text: "View by Type"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.typeOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedTypeFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setTypeFilter(String(opts[index].value || "all"))
                                        viewsPopup.close()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ─────────────────────────
        AppWidgets.SectionDetailPage {
            id: detailPage
            anchors.fill: parent
            open: false
            showHeader: false
            showEdit: false
            showDelete: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            sections: ["Details", "Impact", "Response", "Links"]
            z: 20

            AppWidgets.ContextualActionToolbar {
                width: parent ? parent.width : 0
                showBack: true
                title: root.selectedEntryModel.title || "Register Entry"
                subtitle: root.selectedEntryModel.statusLabel || root.selectedEntryModel.subtitle || ""
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: root._detailActions

                onBackRequested: detailPage.open = false
                onActionTriggered: function(actionId) {
                    if (actionId === "edit") {
                        dialogHost.openEditDialog(root.selectedEntryModel)
                    } else if (actionId === "delete") {
                        dialogHost.openDeleteDialog(root.selectedEntryModel)
                    }
                }
            }

            RegisterDetailPanel {
                width: parent ? parent.width : 0
                detailPage: detailPage
                entryDetail: root.selectedEntryModel
                urgentModel: root.urgentModel
                selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                onEditRequested: dialogHost.openEditDialog(root.selectedEntryModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedEntryModel)
                onUrgentEntrySelected: function(entryId) {
                    if (root.workspaceController !== null) root.workspaceController.selectEntry(entryId)
                }
            }
        }
    }
}
