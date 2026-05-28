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
    property ProjectManagementControllers.ProjectManagementProjectsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.projectsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.projects",
            "title": "Projects",
            "summary": "Project lifecycle, ownership, status, and project list workflows."
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var projectsModel: root.workspaceController
        ? root.workspaceController.projects
        : ({
            "title": "Project Catalog",
            "subtitle": "Create, edit, and review project lifecycle records.",
            "emptyState": "Project-management projects desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedProjectModel: root.workspaceController
        ? root.workspaceController.selectedProject
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a project from the catalog to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    readonly property bool _hasInvCap: root.pmCatalog
        ? root.pmCatalog.hasCapability("inventory.reservations.create") : false
    readonly property bool _hasProcCap: root.pmCatalog
        ? root.pmCatalog.hasCapability("procurement.purchase_orders.read") : false
    readonly property var _detailSections: {
        const secs = ["Overview", "Schedule", "Tasks", "Resources", "Financials", "Risks"]
        if (root._hasInvCap)  secs.push("Material Demand")
        if (root._hasProcCap) secs.push("Procurement")
        secs.push("Documents")
        secs.push("Activity")
        return secs
    }

    readonly property var _tableColumns: [
        { "key": "title",              "label": "Project",  "flex": 2,   "sortable": true  },
        { "key": "statusLabel",        "label": "Status",   "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "clientName",         "label": "Client",   "flex": 1.5, "sortable": true  },
        { "key": "clientContact",      "label": "Contact",  "flex": 1.5                    },
        { "key": "startDateLabel",     "label": "Start",    "flex": 0,   "minWidth": 90    },
        { "key": "endDateLabel",       "label": "Finish",   "flex": 0,   "minWidth": 90    },
        { "key": "plannedBudgetLabel", "label": "Budget",   "flex": 0,   "minWidth": 100   }
    ]

    readonly property var _bulkChangeProperties: {
        const properties = []
        const statusOptions = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || [])
            : []
        if (statusOptions.length > 0) {
            properties.push({
                "id": "status",
                "label": "Status",
                "values": statusOptions
            })
        }
        return properties
    }

    function _statusIndexForValue(statusValue) {
        const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(statusValue || "")) return i
        }
        return 0
    }

    function _loadLazyProjectSection(sectionIndex) {
        if (root.workspaceController === null) return
        const page = detailPageLoader.item
        const secName = page ? (page.sections[sectionIndex] || "") : ""
        if      (secName === "Tasks")     root.workspaceController.loadProjectTasks()
        else if (secName === "Resources") root.workspaceController.loadProjectResources()
        else if (secName === "Financials") root.workspaceController.loadProjectFinancials()
        else if (secName === "Risks")     root.workspaceController.loadProjectRisks()
        else if (secName === "Documents") root.workspaceController.loadProjectDocuments()
        else if (secName === "Activity")  root.workspaceController.loadProjectActivity()
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) {
            detailPage.scrollToSection(sectionIndex)
            root._loadLazyProjectSection(sectionIndex)
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ProjectsDialogHost {
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                workspaceController: root.workspaceController

                onCreateRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createProject(payload)
                }
                onUpdateRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateProject(payload)
                }
                onStatusChangeRequested: function(projectId, statusValue) {
                    if (root.workspaceController !== null) root.workspaceController.setProjectStatus(projectId, statusValue)
                }
                onDeleteRequested: function(projectId) {
                    if (root.workspaceController !== null) root.workspaceController.deleteProject(projectId)
                }
            }
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // ── List page (hidden when detail is open) ────────────────
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
                    message: "Loading projects..."
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
                    searchPlaceholder: "Search projects..."
                    showCreate: true
                    createLabel: "New Project"
                    showFilter: true
                    showCustomize: true
                    showRefresh: true
                    showImport: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: projectsTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onImportRequested: dialogHostLoader.invoke("openImportDialog")
                    onExportRequested: {
                        if (root.workspaceController !== null) root.workspaceController.exportProjects()
                    }
                    onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: projectsTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._tableColumns
                        rows: root.projectsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.projectsModel.emptyState || "No projects available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedProjectIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateProject(rowId)
                            root._openDetail(0)
                        }
                        onViewDetailRequested: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateProject(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setProjectBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) {
                                root.workspaceController.selectVisibleProjects()
                            } else {
                                root.workspaceController.clearProjectBulkSelection()
                            }
                        }
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.projectPage : 1
                        pageSize:     root.workspaceController ? root.workspaceController.projectPageSize : 25
                        totalItems:   root.workspaceController ? root.workspaceController.projectTotalCount : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setProjectPage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setProjectPageSize(pageSize)
                        }
                    }

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
                                text: "Status"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._statusIndexForValue(
                                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opt = root.workspaceController
                                        ? (root.workspaceController.statusOptions || [])[index]
                                        : null
                                    if (opt && root.workspaceController)
                                        root.workspaceController.setStatusFilter(String(opt.value || "all"))
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
                                        if (root.workspaceController !== null)
                                            root.workspaceController.setStatusFilter("all")
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

                    AppWidgets.BulkActionBar {
                        id: bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedProjectCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "delete",          "label": "Delete",          "icon": "delete", "danger": true,  "enabled": true },
                            { "id": "change_property", "label": "Change Property", "icon": "edit",   "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null)
                                root.workspaceController.clearProjectBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (actionId === "delete") {
                                bulkDeleteDialog.open()
                            } else if (actionId === "change_property") {
                                bulkChangePropertyPopup.open()
                            }
                        }
                    }

                    AppWidgets.BulkChangePropertyPopup {
                        id: bulkChangePropertyPopup
                        anchorItem: bulkActionBar.actionButtonForId("change_property")
                        selectedCount: root.workspaceController ? root.workspaceController.selectedProjectCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        properties: root._bulkChangeProperties

                        onApplyRequested: function(payload) {
                            if (root.workspaceController === null) return
                            if (payload.propertyId === "status") {
                                root.workspaceController.applyBulkStatus({ "status": payload.value })
                            }
                        }
                    }

                    AppControls.ConfirmationDialog {
                        id: bulkDeleteDialog
                        title: "Delete Selected Projects"
                        closePolicy: Popup.CloseOnEscape
                        confirmLabel: "Delete Projects"
                        confirmIcon: "delete"
                        confirmDanger: true
                        message: {
                            const count = root.workspaceController
                                ? root.workspaceController.selectedProjectCount : 0
                            return "Delete " + count + " selected project(s) and all related planning data?"
                        }
                        supportingText: "This action removes the project records, related tasks, and dependent planning data. It cannot be undone."

                        onConfirmed: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.bulkDeleteProjects(
                                    root.workspaceController.selectedProjectIds
                                )
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ──────────────────
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
                sections: root._detailSections
                z: 20
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyProjectSection(root._pendingDetailSection)
                }

                onSectionChanged: function(index) {
                    root._loadLazyProjectSection(index)
                }

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedProjectModel.title || "Project Details"
                    subtitle: root.selectedProjectModel.statusLabel || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: [
                        { "id": "edit",   "label": "Edit",   "icon": "edit",    "enabled": true, "danger": false },
                        { "id": "status", "label": "Status", "icon": "approve", "enabled": true, "danger": false },
                        { "id": "delete", "label": "Delete", "icon": "delete",  "enabled": true, "danger": true  }
                    ]

                    onBackRequested: {
                        root._detailOpen = false
                    }
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedProjectModel)
                        } else if (actionId === "status") {
                            dialogHostLoader.invoke("openStatusDialog", root.selectedProjectModel)
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedProjectModel)
                        }
                    }
                }

                ProjectsDetailSection {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    pmCatalog: root.pmCatalog
                    projectDetail: root.selectedProjectModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedProjectModel)
                    onStatusRequested: dialogHostLoader.invoke("openStatusDialog", root.selectedProjectModel)
                    onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedProjectModel)
                }
            }
        }
    }
}

