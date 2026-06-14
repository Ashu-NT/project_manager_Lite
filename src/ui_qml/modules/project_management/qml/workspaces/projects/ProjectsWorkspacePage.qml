pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components
import "dialogs" as Dialogs
import "sections" as Sections
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementProjectsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.projectsWorkspace
        : null

    // ── State management ──────────────────────────────────────────────────
    ProjectsWorkspaceState {
        id: state
        pmCatalog: root.pmCatalog
        workspaceController: root.workspaceController
    }

    // ── Convenience aliases ────────────────────────────────────────────────
    readonly property var workspaceModel: state.workspaceModel
    readonly property var overviewModel: state.overviewModel
    readonly property var projectsModel: state.projectsModel
    readonly property var selectedProjectModel: state.selectedProjectModel
    readonly property var projectTasksModel: state.projectTasksModel
    readonly property var projectResourcesModel: state.projectResourcesModel

    // ── Column management ─────────────────────────────────────────────────
    property var _columns: state.columns

    function _saveColumnState(columns) {
        state.saveColumnState(columns)
        root._columns = state.columns
    }

    // ── Detail page state ─────────────────────────────────────────────────
    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item
    readonly property var _detailActions: {
        const idx = detailPage ? detailPage.activeSectionIndex : 0
        return state.detailActionsForSection(idx, {
            "selectedProjectResourceId": root.workspaceController
                ? root.workspaceController.selectedProjectResourceId : ""
        })
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) {
            detailPage.scrollToSection(sectionIndex)
            state.lazyLoadDetailSection(detailPage, sectionIndex)
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.ProjectsDialogHost {
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                workspaceController: root.workspaceController

                onDeleteRequested: function(projectId) {
                    if (root.workspaceController !== null) root.workspaceController.deleteProject(projectId)
                }
            }
        }
    }

    FileDialog {
        id: _exportDialog
        title: "Export Projects"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: {
            if (root.workspaceController !== null) {
                const cols = state.columns.filter(function(c) { return c.visible !== false })
                    .map(function(c) { return { "key": c.key, "label": c.label } })
                root.workspaceController.exportProjects(cols, String(selectedFile || ""))
            }
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // ── List page ─────────────────────────────────────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen

            Components.ProjectsListPage {
                id: listPage
                anchors.fill: parent
                workspaceController: root.workspaceController
                state: state
                overviewModel: root.overviewModel
                projectsModel: root.projectsModel
                selectedProjectModel: root.selectedProjectModel

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activateProject(rowId)
                    root._openDetail(0)
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setProjectBulkSelection(rowId, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleProjects()
                    else root.workspaceController.clearProjectBulkSelection()
                }
                onColumnsStateChanged: function(columns) {
                    if (root.workspaceController !== null) root._saveColumnState(columns)
                }
                onSearchChanged: function(text) {
                    if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                }
                onFilterClicked: filterPopup.open()
                onRefreshRequested: {
                    if (root.workspaceController !== null) root.workspaceController.refresh()
                }
                onImportRequested: {
                    if (root.pmCatalog ? root.pmCatalog.pmCapabilityController.canImport : true)
                        dialogHostLoader.invoke("openImportDialog")
                }
                onExportRequested: _exportDialog.open()
                onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
                onBulkCancelRequested: {
                    if (root.workspaceController !== null)
                        root.workspaceController.clearProjectBulkSelection()
                }
                onBulkActionRequested: function(actionId) {
                    if (actionId === "delete") {
                        _bulkDeleteDialog.open()
                    } else if (actionId === "change_property") {
                        _bulkChangePopup.open()
                    }
                }
            }

            Components.ProjectsFilterPopup {
                id: filterPopup
                workspaceController: root.workspaceController
                state: state
                anchorItem: listPage.filterButtonItem
            }

            AppWidgets.BulkChangePropertyPopup {
                id: _bulkChangePopup
                anchorItem: listPage.bulkActionBar.actionButtonForId("change_property")
                selectedCount: root.workspaceController ? root.workspaceController.selectedProjectCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                properties: state.bulkChangeProperties

                onApplyRequested: function(payload) {
                    if (root.workspaceController === null) return
                    if (payload.propertyId === "status")
                        root.workspaceController.applyBulkStatus({ "status": payload.value })
                }
            }

            AppControls.ConfirmationDialog {
                id: _bulkDeleteDialog
                title: "Delete Selected Projects"
                closePolicy: Popup.CloseOnEscape
                confirmLabel: "Delete Projects"
                confirmIcon: "delete"
                confirmDanger: true
                message: {
                    const count = root.workspaceController ? root.workspaceController.selectedProjectCount : 0
                    return "Delete " + count + " selected project(s) and all related planning data?"
                }
                supportingText: "This action removes the project records, related tasks, and dependent planning data. It cannot be undone."

                onConfirmed: {
                    if (root.workspaceController !== null)
                        root.workspaceController.bulkDeleteProjects(root.workspaceController.selectedProjectIds)
                }
            }
        }

        // ── Detail page (covers full area, z:20) ──────────────────────────
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
                id: _projectDetailPage
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: state.detailSections
                z: 20
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    state.lazyLoadDetailSection(_projectDetailPage, root._pendingDetailSection)
                }

                onSectionChanged: function(index) {
                    state.lazyLoadDetailSection(_projectDetailPage, index)
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedProjectModel.title || "Project Details"
                    subtitle: root.selectedProjectModel.statusLabel || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedProjectModel)
                        } else if (actionId === "status") {
                            dialogHostLoader.invoke("openStatusDialog", root.selectedProjectModel)
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedProjectModel)
                        } else if (actionId === "edit_project_resource" && projectsDetailPanel) {
                            projectsDetailPanel.openSelectedProjectResourceEditDialog()
                        } else if (actionId === "remove_project_resource" && projectsDetailPanel) {
                            projectsDetailPanel.confirmSelectedProjectResourceRemoval()
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.ProjectsDetailPanel {
                    id: projectsDetailPanel
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    pmCatalog: root.pmCatalog
                    projectDetail: root.selectedProjectModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    sectionErrors: root.workspaceController ? root.workspaceController.sectionErrors : ({})
                    projectTasksModel: root.projectTasksModel
                    projectTasksTableModel: root.workspaceController ? root.workspaceController.projectTasksTableModel : null
                    projectResourcesModel: root.projectResourcesModel
                    projectResourcesTableModel: root.workspaceController ? root.workspaceController.projectResourcesTableModel : null
                    assignableResourceOptions: root.workspaceController ? (root.workspaceController.assignableResourceOptions || []) : []
                    selectedProjectResourceId: root.workspaceController ? root.workspaceController.selectedProjectResourceId : ""
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedProjectModel)
                    onStatusRequested: dialogHostLoader.invoke("openStatusDialog", root.selectedProjectModel)
                    onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedProjectModel)
                }
            }
        }
    }
}
