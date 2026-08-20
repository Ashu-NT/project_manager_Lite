pragma ComponentBehavior: Bound

import QtQuick
import Shell.Context 1.0 as ShellContexts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ShellContexts.ShellContext shellModel
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    readonly property ProjectManagementControllers.PMWorkspaceNavigationController pmNavigation: root.pmCatalog
        ? root.pmCatalog.pmNavigation
        : null
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
    readonly property var taskTimeSummaryModel: state.taskTimeSummaryModel
    readonly property var taskTimeEntriesPageModel: state.taskTimeEntriesPageModel
    readonly property var selectedTimeEntryModel: state.selectedTimeEntryModel
    readonly property var collaborationCommentsModel: state.collaborationCommentsModel
    readonly property var collaborationPresenceModel: state.collaborationPresenceModel
    readonly property var skillRequirementsModel: state.skillRequirementsModel
    readonly property var scheduleImpactModel: state.scheduleImpactModel
    readonly property var scheduleImpactPreviewModel: state.scheduleImpactPreviewModel
    readonly property var taskActivityModel: state.taskActivityModel

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
    property var _dependencyImpactPreview: ({})
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

    function _openTimesheetsRoute() {
        state.openTimesheetsRoute()
    }

    function _openProjectResourcesRoute() {
        state.openProjectResourcesRoute()
    }

    function _openFilterPopup() {
        filterPopup.open()
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

    function _navigationSectionIndex(sectionId) {
        const normalized = String(sectionId || "").trim().toLowerCase()
        if (!normalized.length) return 0
        for (let index = 0; index < root._detailSections.length; index += 1) {
            if (String(root._detailSections[index] || "").trim().toLowerCase() === normalized) {
                return index
            }
        }
        return 0
    }

    function _applyPmNavigationIntent() {
        const navigation = root.pmNavigation
        if (!navigation || navigation.workspaceKey !== "tasks") return
        const routeState = navigation.routeState || ({})
        const taskId = String(routeState.entityId || "").trim()
        if (!taskId.length || root.workspaceController === null) return
        root.workspaceController.activateTask(taskId)
        root._openDetail(root._navigationSectionIndex(routeState.section))
    }

    Connections {
        target: root.pmNavigation

        function onRouteStateChanged() {
            Qt.callLater(root._applyPmNavigationIntent)
        }
    }

    Component.onCompleted: Qt.callLater(root._applyPmNavigationIntent)

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
                wbsParentOptions: root.workspaceController ? (root.workspaceController.wbsParentOptions || []) : []
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
                        } else if (actionId === "move_wbs") {
                            dialogHostLoader.invoke("openWbsMoveDialog", root.selectedTaskModel)
                        } else if (actionId === "progress") {
                            dialogHostLoader.invoke("openProgressDialog", root.selectedTaskModel)
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedTaskModel)
                        } else if (actionId === "reserve_material") {
                            root._openTaskReservationsRoute()
                        } else if (actionId === "edit_dependency" && tasksDetailPanel) {
                            tasksDetailPanel.openSelectedDependencyEditor()
                        } else if (actionId === "remove_dependency" && root._selectedDependencyItem) {
                            dialogHostLoader.invoke("openDeleteDependencyDialog", root._selectedDependencyItem)
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
                    projectResourceUsage: (root.workspaceController && root.workspaceController.assignmentsController)
                        ? root.workspaceController.assignmentsController.projectResourceUsage : null

                    dependenciesModel: root.dependenciesModel
                    dependenciesTableModel: root.workspaceController ? root.workspaceController.dependenciesTableModel : null
                    dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []
                    dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []
                    dependencyImpactPreview: root._dependencyImpactPreview

                    taskTimeSummary: root.taskTimeSummaryModel
                    taskTimeEntriesPage: root.taskTimeEntriesPageModel
                    timeEntriesTableModel: root.workspaceController ? root.workspaceController.timeEntriesTableModel : null
                    selectedTimeEntryModel: root.selectedTimeEntryModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedTimeEntryId : ""
                    timeAssignmentOptions: root.workspaceController ? (root.workspaceController.timeAssignmentOptions || []) : []
                    timeResourceFilter: root.workspaceController ? root.workspaceController.timeResourceFilter : ""

                    collaborationCommentsModel: root.collaborationCommentsModel
                    collaborationPresenceModel: root.collaborationPresenceModel
                    selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                    canOpenReservations: root._hasInvResCap
                    canOpenProcurement: root._hasProcReqCap
                    skillRequirementsModel: root.skillRequirementsModel
                    scheduleImpactModel: root.scheduleImpactModel
                    scheduleImpactPreviewModel: root.scheduleImpactPreviewModel
                    taskActivityModel: root.taskActivityModel

                    onRetrySectionRequested: function(sectionName) {
                        const idx = (root._detailSections || []).indexOf(sectionName)
                        if (idx >= 0) root._loadLazyDetailSection(idx)
                    }
                    onCreateAssignmentRequested: dialogHostLoader.invoke("openCreateAssignmentDialog", root.selectedTaskModel)
                    onAssignmentSelected: function(assignmentId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectAssignment(assignmentId)
                        }
                    }
                    onAssignmentPreviewRequested: function(projectResourceId, taskId) {
                        // Row selection only loads the Project Resource
                        // Context (already-authoritative usage fact) --
                        // previewAssignment() is the hypothetical "what if"
                        // check reserved for the create/edit dialog, since
                        // calling it here with no proposedAllocationPercent/
                        // excludeAssignmentId would double-count this very
                        // assignment's own existing commitment.
                        if (root.workspaceController !== null && projectResourceId.length > 0) {
                            root.workspaceController.assignmentsController.loadProjectResourceUsage(
                                projectResourceId
                            )
                        }
                    }
                    onEditAllocationRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openEditAssignmentAllocationDialog", assignmentData, root.selectedTaskModel)
                    }
                    onEditPlannedHoursRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openEditAssignmentPlannedHoursDialog", assignmentData)
                    }
                    onDeleteAssignmentRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openDeleteAssignmentDialog", assignmentData)
                    }
                    onAcceptAssignmentRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openAssignmentResponseDialog", "accept", assignmentData)
                    }
                    onDeclineAssignmentRequested: function(assignmentData) {
                        dialogHostLoader.invoke("openAssignmentResponseDialog", "decline", assignmentData)
                    }

                    onCreateDependencyRequested: dialogHostLoader.invoke("openCreateDependencyDialog", root.selectedTaskModel)
                    onDependencySelectionChanged: function(dependencyData) {
                        root._selectedDependencyItem = dependencyData || null
                        if (!dependencyData) {
                            root._dependencyImpactPreview = ({})
                        }
                    }
                    onDependencyPreviewRequested: function(dependencyId) {
                        if (root.workspaceController !== null && dependencyId.length > 0) {
                            root._dependencyImpactPreview = root.workspaceController.dependenciesController.previewDeleteDependency(dependencyId) || {}
                        }
                    }
                    onEditDependencyRequested: function(payload) {
                        dialogHostLoader.invoke("openEditDependencyDialog", payload)
                    }
                    onDeleteDependencyRequested: function(dependencyData) {
                        dialogHostLoader.invoke("openDeleteDependencyDialog", dependencyData)
                    }
                    onOpenTaskRequested: function(taskId) {
                        if (root.workspaceController !== null && taskId.length > 0) {
                            root.workspaceController.activateTask(taskId)
                        }
                        root._openDetail(0)
                    }
                    onScheduleImpactPreviewRequested: function(delayWorkingDays) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.previewTaskScheduleImpact(delayWorkingDays)
                        }
                    }

                    onTimeResourceFilterRequested: function(resourceId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.filterTaskTimeEntriesByResource(resourceId)
                        }
                    }
                    onTimePageRequested: function(page) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setTaskTimeEntriesPage(page)
                        }
                    }
                    onGoToAssignmentRequested: function(assignmentId) {
                        if (root.workspaceController !== null && assignmentId.length > 0) {
                            root.workspaceController.selectAssignment(assignmentId)
                        }
                        const idx = (root._detailSections || []).indexOf("Assignments")
                        if (idx >= 0 && root.detailPage) {
                            root.detailPage.scrollToSection(idx)
                            root._loadLazyDetailSection(idx)
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
                    onOpenTimesheetsRequested: root._openTimesheetsRoute()
                    onManageProjectResourcesRequested: root._openProjectResourcesRoute()

                    onComposeRequested: dialogHostLoader.invoke("openTaskCollaborationDialog", root.selectedTaskModel)
                    onCommentReplyRequested: function(commentData) {
                        dialogHostLoader.invoke(
                            "openTaskCommentReplyDialog",
                            commentData,
                            root.selectedTaskModel
                        )
                    }
                    onCommentEditRequested: function(commentData) {
                        dialogHostLoader.invoke(
                            "openTaskCommentEditDialog",
                            commentData,
                            root.selectedTaskModel
                        )
                    }
                    onCommentDeleteRequested: function(commentData) {
                        dialogHostLoader.invoke("openTaskCommentDeleteDialog", commentData)
                    }
                    onCommentReactionRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.reactToTaskComment(payload)
                        }
                    }
                    onCommentReactionRemovalRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.removeTaskCommentReaction(payload)
                        }
                    }
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
