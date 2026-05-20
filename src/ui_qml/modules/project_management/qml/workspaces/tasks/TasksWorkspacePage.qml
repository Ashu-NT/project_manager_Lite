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
    property ProjectManagementControllers.ProjectManagementTasksWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.tasksWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.tasks",
            "title": "Tasks",
            "summary": "Task planning, progress, dependencies, assignments, and execution state.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget tasks workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var tasksModel: root.workspaceController
        ? root.workspaceController.tasks
        : ({
            "title": "Task Catalog",
            "subtitle": "Edit delivery tasks, progress, and execution priorities.",
            "emptyState": "Project-management tasks desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedTaskModel: root.workspaceController
        ? root.workspaceController.selectedTask
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a task from the catalog to review details or update progress.",
            "fields": [],
            "state": {}
        })
    readonly property var assignmentsModel: root.workspaceController
        ? root.workspaceController.assignments
        : ({
            "title": "Assignments",
            "subtitle": "Resource allocations and logged effort for this task.",
            "emptyState": "Select a task to review assignments and effort coverage.",
            "items": []
        })
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({
            "title": "Dependencies",
            "subtitle": "Sequencing links and lag settings for this task.",
            "emptyState": "Select a task to review predecessor and successor links.",
            "items": []
        })
    readonly property var timeAssignmentSummaryModel: root.workspaceController
        ? root.workspaceController.timeAssignmentSummary
        : ({
            "title": "",
            "subtitle": "",
            "emptyState": "Select a task assignment to review detailed time entries, period status, and labor totals.",
            "fields": [],
            "state": {}
        })
    readonly property var timeEntriesModel: root.workspaceController
        ? root.workspaceController.timeEntries
        : ({
            "title": "Time Entries",
            "subtitle": "Detailed labor entries for the selected task assignment.",
            "emptyState": "Select a task assignment to review or capture labor entries.",
            "items": []
        })
    readonly property var selectedTimeEntryModel: root.workspaceController
        ? root.workspaceController.selectedTimeEntry
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an entry from the period list to review or edit its captured labor note.",
            "fields": [],
            "state": {}
        })
    readonly property var collaborationCommentsModel: root.workspaceController
        ? root.workspaceController.collaborationComments
        : ({
            "title": "Task Collaboration",
            "subtitle": "Comments, mentions, attachments, and linked shared documents for the selected task.",
            "emptyState": "Select a task to review collaboration updates and post comments.",
            "items": []
        })
    readonly property var collaborationPresenceModel: root.workspaceController
        ? root.workspaceController.collaborationPresence
        : ({
            "title": "Active Presence",
            "subtitle": "People currently reviewing or updating the selected task.",
            "emptyState": "Select a task to review active collaboration presence.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _tableColumns: [
        { "key": "title",          "label": "Task",      "flex": 2,   "sortable": true  },
        { "key": "statusLabel",    "label": "Status",    "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "projectName",    "label": "Project",   "flex": 1.5, "sortable": true  },
        { "key": "priorityLabel",  "label": "Priority",  "flex": 0,   "minWidth": 80, "type": "status"   },
        { "key": "startDateLabel", "label": "Start",     "flex": 0,   "minWidth": 90    },
        { "key": "endDateLabel",   "label": "Finish",    "flex": 0,   "minWidth": 90    },
        { "key": "progressValue",  "label": "Progress",  "flex": 1,   "minWidth": 110, "type": "progress" }
    ]

    TasksDialogHost {
        id: dialogHost

        selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
        selectedTaskData: root.selectedTaskModel
        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
        dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []
        dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []
        collaborationMentionOptions: root.workspaceController ? (root.workspaceController.collaborationMentionOptions || []) : []
        collaborationDocumentOptions: root.workspaceController ? (root.workspaceController.collaborationDocumentOptions || []) : []
        selectedTaskIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createTask(payload)
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateTask(payload)
        }
        onProgressRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateProgress(payload)
        }
        onDeleteRequested: function(taskId) {
            if (root.workspaceController !== null) root.workspaceController.deleteTask(taskId)
        }
        onCreateAssignmentRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createAssignment(payload)
        }
        onUpdateAssignmentAllocationRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateAssignmentAllocation(payload)
        }
        onSetAssignmentHoursRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.setAssignmentHours(payload)
        }
        onDeleteAssignmentRequested: function(assignmentId) {
            if (root.workspaceController !== null) root.workspaceController.deleteAssignment(assignmentId)
        }
        onCreateDependencyRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createDependency(payload)
        }
        onDeleteDependencyRequested: function(dependencyId) {
            if (root.workspaceController !== null) root.workspaceController.deleteDependency(dependencyId)
        }
        onPostTaskCommentRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.postTaskComment(payload)
        }
        onBulkDeleteRequested: function(taskIds) {
            if (root.workspaceController !== null) root.workspaceController.bulkDeleteTasks(taskIds)
        }
        onTaskPresenceStarted: function(taskId, activity) {
            if (root.workspaceController !== null) root.workspaceController.beginTaskPresence(taskId, activity)
        }
        onTaskPresenceEnded: function(taskId) {
            if (root.workspaceController !== null) root.workspaceController.endTaskPresence(taskId)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        ProjectManagementWidgets.WorkspaceStateBanner {
            Layout.fillWidth: true
            isLoading: root.workspaceController ? root.workspaceController.isLoading : false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
            feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        ProjectManagementWidgets.WorkspaceStatusSection {
            visible: false
            Layout.fillWidth: true
            migrationStatus: root.workspaceController
                ? "QML task execution, advanced filters, saved views, bulk actions, collaboration, and time-entry slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Task catalog, advanced task-query filters, saved filter views, bulk status/delete plus undo/redo flows, collaboration status signals, progress updates, assignment management, dependency flows, task-level collaboration, and assignment-period labor capture now run through typed PM controllers backed by the task, collaboration, and timesheets desktop APIs."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search tasks…"
            showCreate: true
            createLabel: "New Task"
            showFilter: true
            showCustomize: true
            showViews: true
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onFilterClicked:   filterPopup.open()
            onCustomizeClicked: tasksTable.openColumnCustomizer()
            onViewsClicked:    viewsPopup.open()
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: dialogHost.openCreateDialog()
        }

        // Contextual action toolbar — shown when a task row is selected
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible:  String(root.selectedTaskModel.id || "").length > 0
            title:    root.selectedTaskModel.title || ""
            subtitle: root.selectedTaskModel.statusLabel || ""
            busy:     root.workspaceController ? root.workspaceController.isBusy : false
            actions: [
                { id: "details",  label: "Details",  icon: "view",   enabled: true,  danger: false },
                { id: "edit",     label: "Edit",     icon: "edit",   enabled: true,  danger: false },
                { id: "progress", label: "Progress", icon: "approve",enabled: true,  danger: false },
                { id: "delete",   label: "Delete",   icon: "delete", enabled: true,  danger: true  }
            ]
            onActionTriggered: function(id) {
                if (id === "details")  { detailPage.open = true }
                else if (id === "edit")     { dialogHost.openEditDialog(root.selectedTaskModel) }
                else if (id === "progress") { dialogHost.openProgressDialog(root.selectedTaskModel) }
                else if (id === "delete")   { dialogHost.openDeleteDialog(root.selectedTaskModel) }
            }
        }

        // ── Full-width table with full-page detail view ───────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: tasksTable
                anchors.fill: parent
                multiSelect: true
                columns: root._tableColumns
                rows: root.tasksModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectTask(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectTask(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectTask(rowId)
                    detailPage.open = true
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null) root.workspaceController.setTaskBulkSelection(rowId, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController !== null) {
                        if (allSelected) root.workspaceController.selectVisibleTasks()
                        else root.workspaceController.clearTaskBulkSelection()
                    }
                }
                onSortRequested: function(key) {}
            }

            // Filter flyout popup anchored to the DataTable
            Popup {
                id: filterPopup
                parent: tasksTable
                width: 280
                padding: 12
                x: tasksTable.width - width - 4
                y: 30
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius:       Theme.AppTheme.radiusLg
                    color:        Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.divider
                    border.width: 1
                }

                ColumnLayout {
                    width: parent.width
                    spacing: 8

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
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.selectProject(String(opts[index].value || ""))
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
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setStatusFilter(String(opts[index].value || "all"))
                        }
                    }

                    Label {
                        text: "Priority"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setPriorityFilter(String(opts[index].value || "all"))
                        }
                    }

                    Label {
                        text: "Schedule"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.scheduleOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.scheduleOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setScheduleFilter(String(opts[index].value || "all"))
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
                                if (root.workspaceController !== null) root.workspaceController.clearFilters()
                                filterPopup.close()
                            }
                        }

                        AppControls.PrimaryButton {
                            Layout.fillWidth: true
                            text: "Apply"
                            iconName: "filter"
                            onClicked: {
                                if (root.workspaceController !== null) root.workspaceController.applySelectedTaskView()
                                filterPopup.close()
                            }
                        }
                    }
                }
            }

            // Saved views popup
            Popup {
                id: viewsPopup
                parent: tasksTable
                width: 220
                padding: Theme.AppTheme.marginMd
                x: tasksTable.width - width - 4
                y: 30
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius:       Theme.AppTheme.radiusLg
                    color:        Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.divider
                    border.width: 1
                }

                ColumnLayout {
                    width: parent.width
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        text: "Saved Views"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    ComboBox {
                        id: _viewsCombo
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.taskViewOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.taskViewOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.selectTaskView(String(opts[index].value || ""))
                        }
                    }

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        text: "Apply View"
                        iconName: "register"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onClicked: {
                            if (root.workspaceController !== null) root.workspaceController.applySelectedTaskView()
                            viewsPopup.close()
                        }
                    }
                }
            }

            // Floating bulk action bar
            AppWidgets.BulkActionBar {
                id: bulkBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { id: "delete",          label: "Delete",          icon: "delete", danger: true,  enabled: true },
                    { id: "change_property", label: "Change Property", icon: "edit",   danger: false, enabled: true }
                ]
                onCancelRequested: {
                    if (root.workspaceController !== null) root.workspaceController.clearTaskBulkSelection()
                }
                onActionTriggered: function(id) {
                    if (id === "delete") {
                        dialogHost.openBulkDeleteDialog(
                            root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []
                        )
                    } else if (id === "change_property") {
                        changePropertyPopup.parent = bulkBar
                        changePropertyPopup.x = (bulkBar.width - changePropertyPopup.width) / 2
                        changePropertyPopup.y = -changePropertyPopup.height - Theme.AppTheme.spacingXs
                        changePropertyPopup.open()
                    }
                }
            }

            // Bulk change property popup
            AppWidgets.BulkChangePropertyPopup {
                id: changePropertyPopup
                selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                properties: [
                    {
                        id: "status",
                        label: "Status",
                        values: root.workspaceController ? (root.workspaceController.bulkStatusOptions || []) : []
                    }
                ]
                onApplyRequested: function(payload) {
                    if (root.workspaceController !== null && payload.propertyId === "status") {
                        root.workspaceController.applyBulkStatus({ status: payload.value })
                    }
                }
            }

            // Full-page detail view
            AppWidgets.SectionDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root.selectedTaskModel.title || "Task Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Details", "Assignments", "Dependencies", "Time", "Activity"]
                showEdit: true
                showDelete: true

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHost.openEditDialog(root.selectedTaskModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedTaskModel)

                TasksDetailPanel {
                    width: parent.width
                    detailPage: detailPage
                    taskDetail: root.selectedTaskModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    assignmentsModel: root.assignmentsModel
                    selectedAssignmentId: root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
                    assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []

                    dependenciesModel: root.dependenciesModel
                    dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []

                    timeAssignmentSummaryModel: root.timeAssignmentSummaryModel
                    timeEntriesModel: root.timeEntriesModel
                    selectedTimeEntryModel: root.selectedTimeEntryModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedTimeEntryId : ""
                    periodOptions: root.workspaceController ? (root.workspaceController.timePeriodOptions || []) : []
                    selectedPeriodStart: root.workspaceController ? root.workspaceController.selectedTimePeriodStart : ""

                    collaborationCommentsModel: root.collaborationCommentsModel
                    collaborationPresenceModel: root.collaborationPresenceModel
                    selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""

                    onEditRequested: dialogHost.openEditDialog(root.selectedTaskModel)
                    onProgressRequested: dialogHost.openProgressDialog(root.selectedTaskModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedTaskModel)

                    onCreateAssignmentRequested: dialogHost.openCreateAssignmentDialog(root.selectedTaskModel)
                    onAssignmentSelected: function(assignmentId) {
                        if (root.workspaceController !== null) root.workspaceController.selectAssignment(assignmentId)
                    }
                    onEditAllocationRequested: function(assignmentData) {
                        dialogHost.openEditAssignmentAllocationDialog(assignmentData, root.selectedTaskModel)
                    }
                    onSetHoursRequested: function(assignmentData) {
                        dialogHost.openAssignmentHoursDialog(assignmentData)
                    }
                    onDeleteAssignmentRequested: function(assignmentData) {
                        dialogHost.openDeleteAssignmentDialog(assignmentData)
                    }

                    onCreateDependencyRequested: dialogHost.openCreateDependencyDialog(root.selectedTaskModel)
                    onDeleteDependencyRequested: function(dependencyData) {
                        dialogHost.openDeleteDependencyDialog(dependencyData)
                    }

                    onPeriodChanged: function(periodStart) {
                        if (root.workspaceController !== null) root.workspaceController.selectTimePeriod(periodStart)
                    }
                    onEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) root.workspaceController.selectTimeEntry(entryId)
                    }
                    onTimeAddRequested: function(payload) {
                        if (root.workspaceController !== null) root.workspaceController.addTaskTimeEntry(payload)
                    }
                    onTimeUpdateRequested: function(payload) {
                        if (root.workspaceController !== null) root.workspaceController.updateTaskTimeEntry(payload)
                    }
                    onTimeDeleteRequested: function(entryId) {
                        if (root.workspaceController !== null) root.workspaceController.deleteTaskTimeEntry(entryId)
                    }
                    onTimeSubmitRequested: function(payload) {
                        if (root.workspaceController !== null) root.workspaceController.submitTaskPeriod(payload)
                    }
                    onTimeLockRequested: function(payload) {
                        if (root.workspaceController !== null) root.workspaceController.lockTaskPeriod(payload)
                    }
                    onTimeUnlockRequested: function(payload) {
                        if (root.workspaceController !== null) root.workspaceController.unlockTaskPeriod(payload)
                    }

                    onComposeRequested: dialogHost.openTaskCollaborationDialog(root.selectedTaskModel)
                    onMarkReadRequested: function(taskId) {
                        if (root.workspaceController !== null) root.workspaceController.markTaskCollaborationRead(taskId)
                    }
                    onCollaborationRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                }
            }
        }
    }
}
