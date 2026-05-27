pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementResourcesWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.resourcesWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.resources",
            "title": "Resources",
            "summary": "Resource capacity, allocation, project assignments, and utilization views."
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var resourcesModel: root.workspaceController
        ? root.workspaceController.resources
        : ({
            "title": "Resource Pool",
            "subtitle": "Manage capacity, worker types, and resource availability.",
            "emptyState": "Project-management resources desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedResourceModel: root.workspaceController
        ? root.workspaceController.selectedResource
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a resource from the pool to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    readonly property var _tableColumns: [
        { "key": "title",              "label": "Employee",      "flex": 2,   "sortable": true  },
        { "key": "statusLabel",        "label": "Load",          "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "department",         "label": "Department",    "flex": 1.2, "sortable": true  },
        { "key": "site",               "label": "Site",          "flex": 1,   "sortable": true  },
        { "key": "role",               "label": "Role",          "flex": 1.2, "sortable": true  },
        { "key": "assignedHoursLabel", "label": "Assigned Hrs",  "flex": 0,   "minWidth": 100   },
        { "key": "availabilityLabel",  "label": "Availability",  "flex": 0,   "minWidth": 100   },
        { "key": "utilizationValue",   "label": "Utilization",   "flex": 1,   "minWidth": 110, "type": "progress" }
    ]

    readonly property var _detailActions: {
        const state = root.selectedResourceModel
            ? (root.selectedResourceModel.state || {}) : {}
        const isActive = state.isActive !== false
        return [
            { "id": "edit",   "label": "Edit",                              "icon": "edit",    "enabled": true, "danger": false },
            { "id": "toggle", "label": isActive ? "Deactivate" : "Activate","icon": isActive ? "close" : "approve", "enabled": true, "danger": false },
            { "id": "delete", "label": "Delete",                            "icon": "delete",  "enabled": true, "danger": true  }
        ]
    }

    function _categoryIndexForValue(v) {
        const opts = root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(v || "")) return i
        }
        return 0
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) {
            detailPage.scrollToSection(sectionIndex)
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ResourcesDialogHost {
                workerTypeOptions: root.workspaceController ? (root.workspaceController.workerTypeOptions || []) : []
                categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                employeeOptions: root.workspaceController ? (root.workspaceController.employeeOptions || []) : []

                onCreateRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createResource(payload)
                }
                onUpdateRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateResource(payload)
                }
                onDeleteRequested: function(resourceId) {
                    if (root.workspaceController !== null) root.workspaceController.deleteResource(resourceId)
                }
            }
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────────
    Item {
        anchors.fill: parent

        // ── List page (hidden when detail is open) ────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen

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
                    message: "Loading resources..."
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
                    searchText: root.workspaceController ? root.workspaceController.searchText : ""
                    searchPlaceholder: "Search resources..."
                    showCreate: true
                    createLabel: "New Resource"
                    showFilter: true
                    showCustomize: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: resourcesTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) root.workspaceController.exportResources()
                    }
                    onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: resourcesTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._tableColumns
                        rows: root.resourcesModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.resourcesModel.emptyState || "No resources available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedResourceId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedResourceIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateResource(rowId)
                            root._openDetail(0)
                        }
                        onViewDetailRequested: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateResource(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setResourceBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) {
                                root.workspaceController.selectVisibleResources()
                            } else {
                                root.workspaceController.clearResourceBulkSelection()
                            }
                        }
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.resourcePage : 1
                        pageSize:     root.workspaceController ? root.workspaceController.resourcePageSize : 25
                        totalItems:   root.workspaceController ? root.workspaceController.resourceTotalCount : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setResourcePage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null) root.workspaceController.setResourcePageSize(pageSize)
                        }
                    }

                    // ── Filter popup ──────────────────────────────────
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

                            AppControls.Label {
                                text: "Active Status"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: [
                                    { "label": "All",      "value": "all"      },
                                    { "label": "Active",   "value": "active"   },
                                    { "label": "Inactive", "value": "inactive" }
                                ]
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: {
                                    const v = root.workspaceController
                                        ? root.workspaceController.selectedActiveFilter : "all"
                                    return v === "active" ? 1 : v === "inactive" ? 2 : 0
                                }
                                onActivated: function(index) {
                                    const vals = ["all", "active", "inactive"]
                                    if (root.workspaceController !== null)
                                        root.workspaceController.setActiveFilter(vals[index] || "all")
                                }
                            }

                            AppControls.Label {
                                text: "Category"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._categoryIndexForValue(
                                    root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opt = root.workspaceController
                                        ? (root.workspaceController.categoryOptions || [])[index]
                                        : null
                                    if (opt && root.workspaceController)
                                        root.workspaceController.setCategoryFilter(String(opt.value || "all"))
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
                                            root.workspaceController.setActiveFilter("all")
                                            root.workspaceController.setCategoryFilter("all")
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

                    // ── Bulk action bar ───────────────────────────────
                    AppWidgets.BulkActionBar {
                        id: bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedResourceCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null)
                                root.workspaceController.clearResourceBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (actionId === "delete") bulkDeleteDialog.open()
                        }
                    }

                    // ── Bulk delete confirmation ───────────────────────
                    AppControls.CenteredDialog {
                        id: bulkDeleteDialog
                        modal: true
                        width: 440
                        title: "Delete Selected Resources"
                        standardButtons: Dialog.Cancel | Dialog.Ok
                        closePolicy: Popup.CloseOnEscape

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surface
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: {
                                    const count = root.workspaceController
                                        ? root.workspaceController.selectedResourceCount : 0
                                    return "Delete " + count + " selected resource(s) and all related planning data?"
                                }
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "This removes the resource records and any project assignments. It cannot be undone."
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        onAccepted: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.bulkDeleteResources(
                                    root.workspaceController.selectedResourceIds
                                )
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ─────────────────────
        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active: root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Overview", "Assignments", "Capacity", "Calendar", "Skills", "Certifications", "Cost Rates", "Activity"]
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedResourceModel.title || "Resource Details"
                    subtitle: root.selectedResourceModel.statusLabel || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedResourceModel)
                        } else if (actionId === "toggle") {
                            const state = root.selectedResourceModel
                                ? (root.selectedResourceModel.state || {}) : {}
                            if (root.workspaceController !== null && state.resourceId) {
                                root.workspaceController.toggleResourceActive(
                                    String(state.resourceId || ""),
                                    parseInt(String(state.version || "0"), 10)
                                )
                            }
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedResourceModel)
                        }
                    }
                }

                ResourcesDetailSection {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    resourceDetail: root.selectedResourceModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedResourceModel)
                    onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedResourceModel)
                }
            }
        }
    }
}

