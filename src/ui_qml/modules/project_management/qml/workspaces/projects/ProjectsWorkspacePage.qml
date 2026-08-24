pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components
import "dialogs" as Dialogs
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

    readonly property string _inspectorRowId: root.workspaceController
        ? root.workspaceController.selectedProjectId
        : ""
    readonly property var _inspectorItem: {
        const id = root._inspectorRowId
        if (!id) return null
        const items = root.projectsModel.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id || "") === id) return items[i]
        }
        return null
    }
    // Each field gets its own row rather than mashing several concepts
    // into one combined string -- read straight from the catalog row's
    // own `state` (the same fields the table's columns already show, no
    // new fetch), one label per fact instead of a squashed subtitle.
    readonly property var _inspectorSections: {
        const item = root._inspectorItem
        if (!item) return []
        const s = item.state || {}
        const sections = [
            { "label": "Client", "value": String(s.clientLabel || "") },
            { "label": "Site", "value": String(s.siteLabel || "") },
            { "label": "Department", "value": String(s.departmentLabel || "") },
            { "label": "Start", "value": String(s.startDateLabel || "") },
            { "label": "Finish", "value": String(s.endDateLabel || "") },
            { "label": "Contact", "value": String(s.clientContact || "") }
        ]
        if (s.approvedBudgetVisible === true) {
            sections.splice(5, 0, {
                "label": "Approved Budget",
                "value": String(s.approvedBudgetLabel || "")
            })
        }
        return sections
    }

    function _clearInspectorSelection() {
        if (root.workspaceController !== null) root.workspaceController.selectProject("")
    }

    // ── Detail page state ─────────────────────────────────────────────────
    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property real _detailContentViewportHeight: 0
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
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                departmentOptions: root.workspaceController ? (root.workspaceController.departmentOptions || []) : []
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

    // Closes the inspector on Escape, but only when nothing else currently
    // owns Escape -- an open popup/dialog already closes itself on Escape,
    // and should keep exclusive claim to the key while it's up.
    Shortcut {
        sequence: "Escape"
        enabled: root._inspectorItem !== null
            && !root._detailOpen
            && !filterPopup.opened
            && !_bulkChangePopup.opened
            && !_bulkDeleteDialog.opened
            && !(dialogHostLoader.item && dialogHostLoader.item.anyDialogOpen)
        onActivated: root._clearInspectorSelection()
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // Clicking blank workspace background (KPI strip padding, toolbar
        // gaps, pagination-bar margins, etc. -- anywhere that isn't an
        // actual control or the inspector panel itself) closes the
        // inspector, mirroring DataTable's own empty-space-click behavior
        // but covering the whole list/detail region. Declared first so it
        // sits behind `_listPage` in paint/hit order: real controls and
        // popups (which reparent into Overlay.overlay, above everything)
        // claim their own clicks before they ever reach this catcher, and
        // InspectorPanel now swallows clicks on its own blank background
        // too, so this never fires for clicks meant for the panel.
        MouseArea {
            anchors.fill: parent
            visible: !root._detailOpen
            enabled: root._inspectorItem !== null
            onPressed: root._clearInspectorSelection()
        }

        // ── List page ─────────────────────────────────────────────────────
        RowLayout {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen
            spacing: 0

            Components.ProjectsListPage {
                id: listPage
                Layout.fillWidth: true
                Layout.fillHeight: true
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
                    if (root.pmCatalog ? root.pmCatalog.pmCapabilityController.canImport : false)
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

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                visible: root._inspectorItem !== null && Window.width >= Theme.AppTheme.compactContentBreakpoint
                title: root._inspectorItem ? String(root._inspectorItem.title || "") : ""
                statusLabel: root._inspectorItem ? String(root._inspectorItem.statusLabel || "") : ""
                sections: root._inspectorSections
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                editActionLabel: "Edit"
                showEditAction: true

                onCloseRequested: root._clearInspectorSelection()
                onEditRequested: {
                    if (root._inspectorItem) dialogHostLoader.invoke("openEditDialog", root._inspectorItem)
                }
            }

            Components.ProjectsFilterPopup {
                id: filterPopup
                workspaceController: root.workspaceController
                state: state
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
                contentBottomPadding: {
                    const section = state.detailSections[activeSectionIndex] || ""
                    return section === "Tasks" || section === "Resources" || section === "Activity"
                        ? 0 : Theme.AppTheme.pagePadding
                }
                z: 20
                onContentViewportHeightChanged: {
                    root._detailContentViewportHeight = contentViewportHeight
                }
                Component.onCompleted: {
                    root._detailContentViewportHeight = contentViewportHeight
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

                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.ProjectsDetailPanel {
                    id: projectsDetailPanel
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    availableHeight: Math.max(0, root._detailContentViewportHeight - y)
                    pmCatalog: root.pmCatalog
                    projectDetail: root.selectedProjectModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    sectionErrors: root.workspaceController ? root.workspaceController.sectionErrors : ({})
                    projectTasksModel: root.projectTasksModel
                    projectTasksTableModel: root.workspaceController ? root.workspaceController.projectTasksTableModel : null
                    projectResourcesModel: root.projectResourcesModel
                    projectResourcesTableModel: root.workspaceController ? root.workspaceController.projectResourcesTableModel : null
                    projectRisksModel: root.workspaceController ? root.workspaceController.projectRisks : ({})
                    projectActivityModel: root.workspaceController ? root.workspaceController.projectActivity : ({})
                    projectActivityTableModel: root.workspaceController ? root.workspaceController.projectActivityTableModel : null
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
