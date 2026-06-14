pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Shell.Context 1.0 as ShellContexts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components
import "sections" as Sections
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ShellContexts.ShellContext shellModel
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementTasksWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.tasksWorkspace
        : null

    // ── State management (TasksWorkspaceState contains all properties, models, helpers)
    TasksWorkspaceState {
        id: state
        shellModel: root.shellModel
        pmCatalog: root.pmCatalog
        workspaceController: root.workspaceController
    }

    // ── Convenience aliases to state properties ────────────────────────────
    readonly property var workspaceModel: state.workspaceModel
    readonly property var overviewModel: state.overviewModel
    readonly property var tasksModel: state.tasksModel
    readonly property var tasksTableModel: state.tasksTableModel
    readonly property var selectedTaskModel: state.selectedTaskModel
    readonly property var assignmentsModel: state.assignmentsModel
    readonly property var dependenciesModel: state.dependenciesModel
    readonly property var timeAssignmentSummaryModel: state.timeAssignmentSummaryModel
    readonly property var timeEntriesModel: state.timeEntriesModel
    readonly property var selectedTimeEntryModel: state.selectedTimeEntryModel
    readonly property var collaborationCommentsModel: state.collaborationCommentsModel
    readonly property var collaborationPresenceModel: state.collaborationPresenceModel
    readonly property var skillRequirementsModel: state.skillRequirementsModel
    readonly property var scheduleImpactModel: state.scheduleImpactModel

    // ── RBAC capabilities ─────────────────────────────────────────────────
    readonly property bool _hasInvStockCap: state.hasInvStockCapability
    readonly property bool _hasInvResCap: state.hasInvReservationsCapability
    readonly property bool _hasProcReqCap: state.hasProcurementCapability

    // ── Column management ─────────────────────────────────────────────────
    property var _columns: state.columns
    readonly property string _tableId: state.tableId

    function _saveColumnState(columns) {
        state.saveColumnState(columns)
        root._columns = state.columns
    }

    // ── Detail sections and actions ───────────────────────────────────────
    readonly property var _detailSections: state.detailSections
    readonly property var _bulkChangeProperties: state.bulkChangeProperties
    property var _selectedDependencyItem: null
    readonly property var _selectedAssignmentItem: root._itemById(
        root.assignmentsModel ? (root.assignmentsModel.items || []) : [],
        root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
    )

    readonly property var _detailActions: {
        const idx = detailPage ? detailPage.activeSectionIndex : 0
        return state.detailActionsForSection(idx, {
            "assignmentItem": root._selectedAssignmentItem,
            "dependencyItem": root._selectedDependencyItem
        })
    }

    // ── Detail page state ─────────────────────────────────────────────────
    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    on_DetailOpenChanged: {
        if (root.workspaceController !== null) {
            root.workspaceController.setTaskReviewActive(root._detailOpen)
        }
    }

    // ── Helper functions ──────────────────────────────────────────────────
    function _optionIndexForValue(options, value) {
        return state.optionIndexForValue(options, value)
    }

    function _itemById(items, itemId) {
        const id = String(itemId || "")
        if (!id.length) return null
        const list = items || []
        for (let i = 0; i < list.length; i += 1) {
            if (String(list[i].id || "") === id) {
                return list[i]
            }
        }
        return null
    }

    function _loadLazyDetailSection(sectionIndex) {
        state.lazyLoadDetailSection(detailPageLoader.item, sectionIndex)
    }

    function _navigateToRoute(routeId) {
        state.navigateToRoute(routeId)
    }

    function _openTaskReservationsRoute() {
        state.openTaskReservationsRoute()
    }

    function _openTaskProcurementRoute() {
        state.openTaskProcurementRoute()
    }

    function _openFilterPopup() {
        filterPopup.anchorItem = listPage.filterButtonItem
        filterPopup.open()
    }

    function _openViewsPopup() {
        viewsPopup.anchorItem = listPage.viewsButtonItem
        viewsPopup.open()
    }

    function _openBulkChangePropertyPopup() {
        bulkChangePropertyPopup.anchorItem = listPage.bulkActionBar
            ? listPage.bulkActionBar.actionButtonForId("change_property")
            : null
        bulkChangePropertyPopup.open()
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) {
            detailPage.scrollToSection(sectionIndex)
            root._loadLazyDetailSection(sectionIndex)
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            TasksDialogHost {
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                workspaceController: root.workspaceController
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                selectedTaskData: root.selectedTaskModel
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
                dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []
                dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []
                collaborationMentionOptions: root.workspaceController ? (root.workspaceController.collaborationMentionOptions || []) : []
                collaborationDocumentOptions: root.workspaceController ? (root.workspaceController.collaborationDocumentOptions || []) : []
                selectedTaskIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []

                onDeleteRequested: function(taskId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteTask(taskId)
                    }
                }
                onDeleteAssignmentRequested: function(assignmentId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteAssignment(assignmentId)
                    }
                }
                onDeleteDependencyRequested: function(dependencyId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteDependency(dependencyId)
                    }
                }
                onBulkDeleteRequested: function(taskIds) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.bulkDeleteTasks(taskIds)
                    }
                }
                onTaskPresenceStarted: function(taskId, activity) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.beginTaskPresence(taskId, activity)
                    }
                }
                onTaskPresenceEnded: function(taskId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.endTaskPresence(taskId)
                    }
                }
            }
        }
    }

    Components.TasksExportDialog {
        id: exportDialog
        workspaceController: root.workspaceController
        columns: root._columns
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // ── List page (stays visible until detail loader is ready) ───
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen || detailPageLoader.status !== Loader.Ready

            Components.TasksListPage {
                id: listPage
                anchors.fill: parent
                workspaceController: root.workspaceController
                state: state
                overviewModel: root.overviewModel
                tasksModel: root.tasksModel
                tasksTableModel: root.tasksTableModel
                selectedTaskModel: root.selectedTaskModel

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectTask(rowId)
                    }
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.activateTask(rowId)
                    }
                    root._openDetail(0)
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setTaskBulkSelection(rowId, selected)
                    }
                }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) {
                        return
                    }
                    if (allSelected) {
                        root.workspaceController.selectVisibleTasks()
                    } else {
                        root.workspaceController.clearTaskBulkSelection()
                    }
                }
                onColumnsStateChanged: function(columns) {
                    if (root.workspaceController !== null) {
                        root._saveColumnState(columns)
                    }
                }
                onSearchChanged: function(text) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(text)
                    }
                }
                onFilterClicked: root._openFilterPopup()
                onViewsClicked: root._openViewsPopup()
                onRefreshRequested: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
                onExportRequested: exportDialog.open()
                onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
                onBulkCancelRequested: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.clearTaskBulkSelection()
                    }
                }
                onBulkActionRequested: function(actionId) {
                    if (actionId === "delete") {
                        dialogHostLoader.invoke(
                            "openBulkDeleteDialog",
                            root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []
                        )
                    } else if (actionId === "change_property") {
                        root._openBulkChangePropertyPopup()
                    }
                }
            }

            Components.TasksFilterPopup {
                id: filterPopup
                workspaceController: root.workspaceController
                state: state
                anchorItem: listPage.filterButtonItem
            }

            Components.TasksSavedViewsPopup {
                id: viewsPopup
                workspaceController: root.workspaceController
                state: state
                anchorItem: listPage.viewsButtonItem
            }

            AppWidgets.BulkChangePropertyPopup {
                id: bulkChangePropertyPopup
                anchorItem: listPage.bulkActionBar.actionButtonForId("change_property")
                selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                properties: root._bulkChangeProperties

                onApplyRequested: function(payload) {
                    if (root.workspaceController === null) {
                        return
                    }
                    if (payload.propertyId === "status") {
                        root.workspaceController.applyBulkStatus({ "status": payload.value })
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
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                onSectionChanged: function(index) {
                    if ((root._detailSections[index] || "") !== "Dependencies") {
                        root._selectedDependencyItem = null
                    }
                    root._loadLazyDetailSection(index)
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedTaskModel.title || "Task Details"
                    subtitle: root.selectedTaskModel.statusLabel || root.selectedTaskModel.subtitle || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: {
                        root._selectedDependencyItem = null
                        root._detailOpen = false
                    }
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedTaskModel)
                        } else if (actionId === "progress") {
                            dialogHostLoader.invoke("openProgressDialog", root.selectedTaskModel)
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedTaskModel)
                        } else if (actionId === "reserve_material") {
                            root._openTaskReservationsRoute()
                        } else if (actionId === "edit_allocation" && root._selectedAssignmentItem) {
                            dialogHostLoader.invoke(
                                "openEditAssignmentAllocationDialog",
                                root._selectedAssignmentItem,
                                root.selectedTaskModel
                            )
                        } else if (actionId === "set_assignment_hours" && root._selectedAssignmentItem) {
                            dialogHostLoader.invoke("openAssignmentHoursDialog", root._selectedAssignmentItem)
                        } else if (actionId === "remove_assignment" && root._selectedAssignmentItem) {
                            dialogHostLoader.invoke("openDeleteAssignmentDialog", root._selectedAssignmentItem)
                        } else if (actionId === "edit_dependency" && tasksDetailPanel) {
                            tasksDetailPanel.openSelectedDependencyEditor()
                        } else if (actionId === "remove_dependency" && root._selectedDependencyItem) {
                            dialogHostLoader.invoke("openDeleteDependencyDialog", root._selectedDependencyItem)
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

                Panels.TasksDetailPanel {
                    id: tasksDetailPanel
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    pmCatalog: root.pmCatalog
                    taskDetail: root.selectedTaskModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    sectionErrors: root.workspaceController ? root.workspaceController.sectionErrors : ({})

                    assignmentsModel: root.assignmentsModel
                    assignmentsTableModel: root.workspaceController ? root.workspaceController.assignmentsTableModel : null
                    selectedAssignmentId: root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
                    assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
                    assignmentPreview: root.workspaceController ? root.workspaceController.assignmentPreview : null

                    dependenciesModel: root.dependenciesModel
                    dependenciesTableModel: root.workspaceController ? root.workspaceController.dependenciesTableModel : null
                    dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []
                    dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []

                    timeAssignmentSummaryModel: root.timeAssignmentSummaryModel
                    timeEntriesModel: root.timeEntriesModel
                    timeEntriesTableModel: root.workspaceController ? root.workspaceController.timeEntriesTableModel : null
                    selectedTimeEntryModel: root.selectedTimeEntryModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedTimeEntryId : ""
                    timeAssignmentOptions: root.workspaceController ? (root.workspaceController.timeAssignmentOptions || []) : []
                    periodOptions: root.workspaceController ? (root.workspaceController.timePeriodOptions || []) : []
                    selectedPeriodStart: root.workspaceController ? root.workspaceController.selectedTimePeriodStart : ""

                    collaborationCommentsModel: root.collaborationCommentsModel
                    collaborationPresenceModel: root.collaborationPresenceModel
                    selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                    canOpenReservations: root._hasInvResCap
                    canOpenProcurement: root._hasProcReqCap
                    skillRequirementsModel: root.skillRequirementsModel
                    scheduleImpactModel: root.scheduleImpactModel

                    onRetrySectionRequested: function(sectionName) {
                        const page = detailPageLoader.item
                        if (!page) return
                        const idx = page.sections.indexOf(sectionName)
                        if (idx >= 0) root._loadLazyDetailSection(idx)
                    }
                    onCreateAssignmentRequested: dialogHostLoader.invoke("openCreateAssignmentDialog", root.selectedTaskModel)
                    onAssignmentSelected: function(assignmentId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectAssignment(assignmentId)
                        }
                    }
                    onAssignmentPreviewRequested: function(projectResourceId, taskId) {
                        if (root.workspaceController !== null && projectResourceId.length > 0) {
                            root.workspaceController.assignmentsController.previewAssignment({
                                "projectResourceId": projectResourceId,
                                "taskId": taskId
                            })
                        }
                    }
                    onEditAllocationRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openEditAssignmentAllocationDialog", assignmentData, root.selectedTaskModel)
                    }
                    onSetHoursRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openAssignmentHoursDialog", assignmentData)
                    }
                    onDeleteAssignmentRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openDeleteAssignmentDialog", assignmentData)
                    }

                    onCreateDependencyRequested: dialogHostLoader.invoke("openCreateDependencyDialog", root.selectedTaskModel)
                    onDependencySelectionChanged: function(dependencyData) {
                        root._selectedDependencyItem = dependencyData || null
                    }
                    onEditDependencyRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.updateDependency(payload)
                        }
                    }
                    onDeleteDependencyRequested: function(dependencyData) {
                        dialogHostLoader.invoke("openDeleteDependencyDialog", dependencyData)
                    }

                    onTimeAssignmentSelected: function(assignmentId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectAssignment(assignmentId)
                        }
                    }
                    onPeriodChanged: function(periodStart) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectTimePeriod(periodStart)
                        }
                    }
                    onEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectTimeEntry(entryId)
                        }
                    }
                    onTimeAddRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.addTaskTimeEntry(payload)
                        }
                    }
                    onTimeUpdateRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.updateTaskTimeEntry(payload)
                        }
                    }
                    onTimeDeleteRequested: function(entryId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.deleteTaskTimeEntry(entryId)
                        }
                    }
                    onTimeSubmitRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.submitTaskPeriod(payload)
                        }
                    }
                    onTimeLockRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.lockTaskPeriod(payload)
                        }
                    }
                    onTimeUnlockRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.unlockTaskPeriod(payload)
                        }
                    }

                    onComposeRequested: dialogHostLoader.invoke("openTaskCollaborationDialog", root.selectedTaskModel)
                    onMarkReadRequested: function(taskId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.markTaskCollaborationRead(taskId)
                        }
                    }
                    onCollaborationRefreshRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.loadSelectedTaskCollaboration()
                        }
                    }
                    onOpenReservationsRequested: root._openTaskReservationsRoute()
                    onOpenProcurementRequested: root._openTaskProcurementRoute()
                }
            }
        }
    }
}
