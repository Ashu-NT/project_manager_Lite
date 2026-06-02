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

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementResourcesWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.resourcesWorkspace
        : null

    // ── State management ──────────────────────────────────────────────────
    ResourcesWorkspaceState {
        id: state
        pmCatalog: root.pmCatalog
        workspaceController: root.workspaceController
    }

    // ── Convenience aliases ────────────────────────────────────────────────
    readonly property var workspaceModel: state.workspaceModel
    readonly property var overviewModel: state.overviewModel
    readonly property var resourcesModel: state.resourcesModel
    readonly property var selectedResourceModel: state.selectedResourceModel

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

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) detailPage.scrollToSection(sectionIndex)
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.ResourcesDialogHost {
                workerTypeOptions: root.workspaceController ? (root.workspaceController.workerTypeOptions || []) : []
                categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                employeeOptions: root.workspaceController ? (root.workspaceController.employeeOptions || []) : []
                workspaceController: root.workspaceController

                onDeleteRequested: function(resourceId) {
                    if (root.workspaceController !== null) root.workspaceController.deleteResource(resourceId)
                }
            }
        }
    }

    FileDialog {
        id: _exportDialog
        title: "Export Resources"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: {
            if (root.workspaceController !== null) {
                const cols = state.columns.filter(function(c) { return c.visible !== false })
                    .map(function(c) { return { "key": c.key, "label": c.label } })
                root.workspaceController.exportResources(cols, String(selectedFile || ""))
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

            Components.ResourcesListPage {
                id: listPage
                anchors.fill: parent
                workspaceController: root.workspaceController
                state: state
                overviewModel: root.overviewModel
                resourcesModel: root.resourcesModel

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activateResource(rowId)
                    root._openDetail(0)
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setResourceBulkSelection(rowId, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleResources()
                    else root.workspaceController.clearResourceBulkSelection()
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
                onExportRequested: _exportDialog.open()
                onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
            }

            Components.ResourcesFilterPopup {
                id: filterPopup
                workspaceController: root.workspaceController
                state: state
                anchorItem: listPage.filterButtonItem
            }

            // ── Bulk action bar ───────────────────────────────────────────
            AppWidgets.BulkActionBar {
                id: _bulkActionBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.AppTheme.spacingMd + 40
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedResourceCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true }
                ]

                onCancelRequested: {
                    if (root.workspaceController !== null) root.workspaceController.clearResourceBulkSelection()
                }
                onActionTriggered: function(actionId) {
                    if (actionId === "delete") _bulkDeleteDialog.open()
                }
            }

            AppControls.ConfirmationDialog {
                id: _bulkDeleteDialog
                title: "Delete Selected Resources"
                closePolicy: Popup.CloseOnEscape
                confirmLabel: "Delete Resources"
                confirmIcon: "delete"
                confirmDanger: true
                message: {
                    const count = root.workspaceController ? root.workspaceController.selectedResourceCount : 0
                    return "Delete " + count + " selected resource(s) and all related planning data?"
                }
                supportingText: "This removes the resource records and any project assignments. It cannot be undone."

                onConfirmed: {
                    if (root.workspaceController !== null)
                        root.workspaceController.bulkDeleteResources(root.workspaceController.selectedResourceIds)
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
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: state.detailSections
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                onSectionChanged: function(index) {
                    if (index === 1 && root.workspaceController !== null) {
                        root.workspaceController.loadResourceAssignments()
                    }
                }

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedResourceModel.title || "Resource Details"
                    subtitle: root.selectedResourceModel.statusLabel || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: state.detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedResourceModel)
                        } else if (actionId === "toggle") {
                            const st = root.selectedResourceModel
                                ? (root.selectedResourceModel.state || {}) : {}
                            if (root.workspaceController !== null && st.resourceId) {
                                root.workspaceController.toggleResourceActive(
                                    String(st.resourceId || ""),
                                    parseInt(String(st.version || "0"), 10)
                                )
                            }
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedResourceModel)
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

                Sections.ResourcesDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    resourceDetail: root.selectedResourceModel
                    resourceAvailabilityModel: root.workspaceController
                        ? (root.workspaceController.resourceAvailability || {}) : ({})
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    workspaceController: root.workspaceController
                    resourceAssignmentsTableModel: root.workspaceController
                        ? root.workspaceController.resourceAssignmentsTableModel : null
                    canManageSkills: root.pmCatalog ? root.pmCatalog.pmCapabilityController.canManageSkills : true
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedResourceModel)
                    onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedResourceModel)
                    onAddSkillRequested: dialogHostLoader.invoke("openAddSkillDialog")
                    onAddCertificationRequested: dialogHostLoader.invoke("openAddCertificationDialog")
                    onRemoveSkillRequested: function(skillId) {
                        if (root.workspaceController !== null) root.workspaceController.removeSkill(skillId)
                    }
                    onRemoveCertificationRequested: function(certId) {
                        if (root.workspaceController !== null) root.workspaceController.removeCertification(certId)
                    }
                }
            }
        }
    }
}
