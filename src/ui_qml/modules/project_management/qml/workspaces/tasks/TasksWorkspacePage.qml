import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
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
            if (root.workspaceController !== null) {
                root.workspaceController.createTask(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateTask(payload)
            }
        }

        onProgressRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateProgress(payload)
            }
        }

        onDeleteRequested: function(taskId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteTask(taskId)
            }
        }

        onCreateAssignmentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createAssignment(payload)
            }
        }

        onUpdateAssignmentAllocationRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateAssignmentAllocation(payload)
            }
        }

        onSetAssignmentHoursRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.setAssignmentHours(payload)
            }
        }

        onDeleteAssignmentRequested: function(assignmentId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteAssignment(assignmentId)
            }
        }

        onCreateDependencyRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createDependency(payload)
            }
        }

        onDeleteDependencyRequested: function(dependencyId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteDependency(dependencyId)
            }
        }

        onPostTaskCommentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.postTaskComment(payload)
            }
        }

        onBulkDeleteRequested: function(taskIds) {
            if (root.workspaceController !== null) {
                root.workspaceController.bulkDeleteTasks(taskIds)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            TasksMetricsSection {
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
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML task execution, advanced filters, saved views, bulk actions, collaboration, and time-entry slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Task catalog, advanced task-query filters, saved filter views, bulk status/delete plus undo/redo flows, collaboration status signals, progress updates, assignment management, dependency flows, task-level collaboration, and assignment-period labor capture now run through typed PM controllers backed by the task, collaboration, and timesheets desktop APIs."
            }

            TasksFiltersSection {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                priorityOptions: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                scheduleOptions: root.workspaceController ? (root.workspaceController.scheduleOptions || []) : []
                taskViewOptions: root.workspaceController ? (root.workspaceController.taskViewOptions || []) : []
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                selectedPriorityFilter: root.workspaceController ? root.workspaceController.selectedPriorityFilter : "all"
                selectedScheduleFilter: root.workspaceController ? root.workspaceController.selectedScheduleFilter : "all"
                selectedTaskViewName: root.workspaceController ? root.workspaceController.selectedTaskViewName : ""
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onProjectSelected: function(projectId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(projectId)
                    }
                }

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onStatusFilterUpdated: function(statusValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStatusFilter(statusValue)
                    }
                }

                onPriorityFilterUpdated: function(priorityValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setPriorityFilter(priorityValue)
                    }
                }

                onScheduleFilterUpdated: function(scheduleValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setScheduleFilter(scheduleValue)
                    }
                }

                onTaskViewSelected: function(viewName) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectTaskView(viewName)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onClearRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.clearFilters()
                    }
                }

                onApplyTaskViewRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.applySelectedTaskView()
                    }
                }

                onSaveTaskViewRequested: function(viewName) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.saveCurrentTaskView(viewName)
                    }
                }

                onDeleteTaskViewRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteSelectedTaskView()
                    }
                }

                onCreateRequested: function() {
                    dialogHost.openCreateDialog()
                }
            }

            TasksBulkActionsSection {
                Layout.fillWidth: true
                statusOptions: root.workspaceController ? (root.workspaceController.bulkStatusOptions || []) : []
                selectedTaskCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
                selectedTaskDoneCount: root.workspaceController ? root.workspaceController.selectedTaskDoneCount : 0
                visibleTaskCount: (root.tasksModel.items || []).length
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                canUndoTaskAction: root.workspaceController ? root.workspaceController.canUndoTaskAction : false
                canRedoTaskAction: root.workspaceController ? root.workspaceController.canRedoTaskAction : false
                undoLabel: root.workspaceController ? root.workspaceController.nextUndoLabel : ""
                redoLabel: root.workspaceController ? root.workspaceController.nextRedoLabel : ""

                onSelectVisibleRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectVisibleTasks()
                    }
                }

                onClearRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.clearTaskBulkSelection()
                    }
                }

                onApplyStatusRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.applyBulkStatus(payload)
                    }
                }

                onBulkDeleteRequested: function() {
                    dialogHost.openBulkDeleteDialog(
                        root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []
                    )
                }

                onUndoRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.undoLastTaskAction()
                    }
                }

                onRedoRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.redoLastTaskAction()
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                TasksCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    tasksModel: root.tasksModel
                    selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                    selectedTaskIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onTaskSelected: function(taskId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskId)
                        }
                    }

                    onTaskSelectionToggled: function(taskId, selected) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setTaskBulkSelection(taskId, selected)
                        }
                    }

                    onEditRequested: function(taskData) {
                        if (taskData && taskData.id && root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskData.id)
                        }
                        dialogHost.openEditDialog(taskData)
                    }

                    onProgressRequested: function(taskData) {
                        if (taskData && taskData.id && root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskData.id)
                        }
                        dialogHost.openProgressDialog(taskData)
                    }

                    onDeleteRequested: function(taskData) {
                        if (taskData && taskData.id && root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskData.id)
                        }
                        dialogHost.openDeleteDialog(taskData)
                    }
                }

                TasksDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    taskDetail: root.selectedTaskModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.selectedTaskModel)
                    onProgressRequested: dialogHost.openProgressDialog(root.selectedTaskModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedTaskModel)
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                TasksAssignmentsSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    assignmentsModel: root.assignmentsModel
                    selectedAssignmentId: root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    canCreate: !!(root.selectedTaskModel && root.selectedTaskModel.id)
                        && ((root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []).length > 0)

                    onCreateRequested: function() {
                        dialogHost.openCreateAssignmentDialog(root.selectedTaskModel)
                    }
                    onAssignmentSelected: function(assignmentId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectAssignment(assignmentId)
                        }
                    }
                    onEditAllocationRequested: function(assignmentData) {
                        dialogHost.openEditAssignmentAllocationDialog(
                            assignmentData,
                            root.selectedTaskModel
                        )
                    }
                    onSetHoursRequested: function(assignmentData) {
                        dialogHost.openAssignmentHoursDialog(assignmentData)
                    }
                    onDeleteRequested: function(assignmentData) {
                        dialogHost.openDeleteAssignmentDialog(assignmentData)
                    }
                }

                TasksDependenciesSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    dependenciesModel: root.dependenciesModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    canCreate: !!(root.selectedTaskModel && root.selectedTaskModel.id)
                        && ((root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []).length > 0)

                    onCreateRequested: function() {
                        dialogHost.openCreateDependencyDialog(root.selectedTaskModel)
                    }
                    onDeleteRequested: function(dependencyData) {
                        dialogHost.openDeleteDependencyDialog(dependencyData)
                    }
                }
            }

            TasksTimeEntriesSection {
                Layout.fillWidth: true
                assignmentSummary: root.timeAssignmentSummaryModel
                periodOptions: root.workspaceController ? (root.workspaceController.timePeriodOptions || []) : []
                selectedPeriodStart: root.workspaceController ? root.workspaceController.selectedTimePeriodStart : ""
                entriesModel: root.timeEntriesModel
                selectedEntryDetail: root.selectedTimeEntryModel
                selectedEntryId: root.workspaceController ? root.workspaceController.selectedTimeEntryId : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

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

                onAddRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.addTaskTimeEntry(payload)
                    }
                }

                onUpdateRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.updateTaskTimeEntry(payload)
                    }
                }

                onDeleteRequested: function(entryId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteTaskTimeEntry(entryId)
                    }
                }

                onSubmitRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.submitTaskPeriod(payload)
                    }
                }

                onLockRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.lockTaskPeriod(payload)
                    }
                }

                onUnlockRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.unlockTaskPeriod(payload)
                    }
                }
            }

            TasksCollaborationSection {
                Layout.fillWidth: true
                commentsModel: root.collaborationCommentsModel
                presenceModel: root.collaborationPresenceModel
                selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                canCompose: !!(root.selectedTaskModel && root.selectedTaskModel.id)

                onComposeRequested: function() {
                    dialogHost.openTaskCollaborationDialog(root.selectedTaskModel)
                }

                onMarkReadRequested: function(taskId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.markTaskCollaborationRead(taskId)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }
        }
    }
}
