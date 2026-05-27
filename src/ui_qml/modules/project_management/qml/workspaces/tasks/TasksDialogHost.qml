import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property string selectedProjectId: ""
    property var workspaceController: null
    property var projectOptions: []
    property var selectedTaskData: ({})
    property var statusOptions: []
    property var assignmentOptions: []
    property var dependencyTaskOptions: []
    property var dependencyTypeOptions: []
    property var collaborationMentionOptions: []
    property var collaborationDocumentOptions: []
    property var selectedTaskIds: []
    property var editTarget: ({})
    property var progressTarget: ({})
    property var deleteTarget: ({})
    property var assignmentTarget: ({})
    property var dependencyTarget: ({})
    property var collaborationTarget: ({})
    property var bulkDeleteTargetIds: []

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal progressRequested(var payload)
    signal deleteRequested(string taskId)
    signal createAssignmentRequested(var payload)
    signal updateAssignmentAllocationRequested(var payload)
    signal setAssignmentHoursRequested(var payload)
    signal deleteAssignmentRequested(string assignmentId)
    signal createDependencyRequested(var payload)
    signal deleteDependencyRequested(string dependencyId)
    signal postTaskCommentRequested(var payload)
    signal bulkDeleteRequested(var taskIds)
    signal taskPresenceStarted(string taskId, string activity)
    signal taskPresenceEnded(string taskId)

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "projectId": root.selectedProjectId,
                "status": "TODO"
            }
        }
        editorDialog.modeTitle = "Create Task"
        editorDialog.taskData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(taskData) {
        root.editTarget = taskData || ({})
        const state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
        if (state.taskId) {
            root.taskPresenceStarted(String(state.taskId), "editing")
        }
        editorDialog.modeTitle = "Edit Task"
        editorDialog.taskData = root.editTarget
        editorDialog.open()
    }

    function openProgressDialog(taskData) {
        root.progressTarget = taskData || ({})
        const state = root.progressTarget && root.progressTarget.state ? root.progressTarget.state : (root.progressTarget || {})
        if (state.taskId) {
            root.taskPresenceStarted(String(state.taskId), "updating progress")
        }
        progressDialog.taskData = root.progressTarget
        progressDialog.open()
    }

    function openDeleteDialog(taskData) {
        root.deleteTarget = taskData || ({})
        deleteDialog.open()
    }

    function openCreateAssignmentDialog(taskData) {
        root.assignmentTarget = ({})
        assignmentEditorDialog.mode = "create"
        assignmentEditorDialog.taskData = taskData || ({})
        assignmentEditorDialog.assignmentData = ({})
        assignmentEditorDialog.open()
    }

    function openEditAssignmentAllocationDialog(assignmentData, taskData) {
        root.assignmentTarget = assignmentData || ({})
        assignmentEditorDialog.mode = "allocation"
        assignmentEditorDialog.taskData = taskData || root.selectedTaskData || ({})
        assignmentEditorDialog.assignmentData = root.assignmentTarget
        assignmentEditorDialog.open()
    }

    function openAssignmentHoursDialog(assignmentData) {
        root.assignmentTarget = assignmentData || ({})
        assignmentHoursDialog.assignmentData = root.assignmentTarget
        assignmentHoursDialog.open()
    }

    function openDeleteAssignmentDialog(assignmentData) {
        root.assignmentTarget = assignmentData || ({})
        deleteAssignmentDialog.open()
    }

    function openCreateDependencyDialog(taskData) {
        root.dependencyTarget = taskData || ({})
        dependencyEditorDialog.taskData = root.dependencyTarget
        dependencyEditorDialog.open()
    }

    function openDeleteDependencyDialog(dependencyData) {
        root.dependencyTarget = dependencyData || ({})
        deleteDependencyDialog.open()
    }

    function openTaskCollaborationDialog(taskData) {
        root.collaborationTarget = taskData || root.selectedTaskData || ({})
        const state = root.collaborationTarget && root.collaborationTarget.state ? root.collaborationTarget.state : (root.collaborationTarget || {})
        if (state.taskId || state.id) {
            root.taskPresenceStarted(String(state.taskId || state.id), "commenting")
        }
        collaborationComposerDialog.taskData = root.collaborationTarget
        collaborationComposerDialog.open()
    }

    function openBulkDeleteDialog(taskIds) {
        root.bulkDeleteTargetIds = taskIds || root.selectedTaskIds || []
        bulkDeleteDialog.open()
    }

    ProjectManagementDialogs.TaskEditorDialog {
        id: editorDialog
        objectName: "taskEditorDialog"

        projectOptions: root.projectOptions
        selectedProjectId: root.selectedProjectId
        statusOptions: root.statusOptions

        onClosed: {
            const state = root.editTarget && root.editTarget.state
                ? root.editTarget.state
                : (root.editTarget || {})
            if (state.taskId) {
                root.taskPresenceEnded(String(state.taskId))
            }
        }

        onSubmitted: function(payload) {
            const state = root.editTarget && root.editTarget.state
                ? root.editTarget.state
                : (root.editTarget || {})
            if (state.taskId) {
                payload.projectId = String(state.projectId || payload.projectId || root.selectedProjectId || "")
                payload.taskId = String(state.taskId)
                payload.expectedVersion = state.version
                root.updateRequested(payload)
            } else {
                root.createRequested(payload)
            }
            editorDialog.close()
        }
    }

    ProjectManagementDialogs.TaskProgressDialog {
        id: progressDialog
        objectName: "taskProgressDialog"

        statusOptions: root.statusOptions

        onClosed: {
            const state = root.progressTarget && root.progressTarget.state
                ? root.progressTarget.state
                : (root.progressTarget || {})
            if (state.taskId) {
                root.taskPresenceEnded(String(state.taskId))
            }
        }

        onSubmitted: function(payload) {
            root.progressRequested(payload)
            progressDialog.close()
        }
    }

    ProjectManagementDialogs.TaskAssignmentEditorDialog {
        id: assignmentEditorDialog
        objectName: "taskAssignmentEditorDialog"

        resourceOptions: root.assignmentOptions
        workspaceController: root.workspaceController

        onSubmitted: function(payload) {
            if (assignmentEditorDialog.mode === "create") {
                root.createAssignmentRequested(payload)
            } else {
                root.updateAssignmentAllocationRequested(payload)
            }
            assignmentEditorDialog.close()
        }
    }

    ProjectManagementDialogs.TaskAssignmentHoursDialog {
        id: assignmentHoursDialog
        objectName: "taskAssignmentHoursDialog"

        onSubmitted: function(payload) {
            root.setAssignmentHoursRequested(payload)
            assignmentHoursDialog.close()
        }
    }

    ProjectManagementDialogs.TaskDependencyEditorDialog {
        id: dependencyEditorDialog
        objectName: "taskDependencyEditorDialog"

        taskOptions: root.dependencyTaskOptions
        dependencyTypeOptions: root.dependencyTypeOptions

        onSubmitted: function(payload) {
            root.createDependencyRequested(payload)
            dependencyEditorDialog.close()
        }
    }

    ProjectManagementDialogs.TaskCollaborationComposerDialog {
        id: collaborationComposerDialog
        objectName: "taskCollaborationComposerDialog"

        mentionOptions: root.collaborationMentionOptions
        documentOptions: root.collaborationDocumentOptions

        onClosed: {
            const state = root.collaborationTarget && root.collaborationTarget.state
                ? root.collaborationTarget.state
                : (root.collaborationTarget || {})
            if (state.taskId || state.id) {
                root.taskPresenceEnded(String(state.taskId || state.id))
            }
        }

        onSubmitted: function(payload) {
            root.postTaskCommentRequested(payload)
            collaborationComposerDialog.close()
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteDialog
        objectName: "taskDeleteDialog"
        title: "Delete Task"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Task"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.deleteTarget && root.deleteTarget.title
            ? "Delete " + root.deleteTarget.title + " and its dependent planning data?"
            : "Delete the selected task and its dependent planning data?"
        supportingText: "This action removes the task record plus related dependencies, assignments, and linked planning items."

        onConfirmed: {
            const state = root.deleteTarget && root.deleteTarget.state
                ? root.deleteTarget.state
                : (root.deleteTarget || {})
            if (state.taskId) {
                root.deleteRequested(String(state.taskId))
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: bulkDeleteDialog
        objectName: "taskBulkDeleteDialog"
        title: "Bulk Delete Tasks"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Tasks"
        confirmIcon: "delete"
        confirmDanger: true
        message: "Delete " + String((root.bulkDeleteTargetIds || []).length) + " selected tasks and their dependencies/assignments?"
        supportingText: "This action cannot be undone."

        onConfirmed: {
            root.bulkDeleteRequested(root.bulkDeleteTargetIds || [])
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteAssignmentDialog
        objectName: "taskDeleteAssignmentDialog"
        title: "Remove Assignment"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Remove Assignment"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.assignmentTarget && root.assignmentTarget.title
            ? "Remove " + root.assignmentTarget.title + " from the selected task?"
            : "Remove the selected assignment?"
        supportingText: "This removes the assignment from the task but does not delete the underlying resource."

        onConfirmed: {
            const state = root.assignmentTarget && root.assignmentTarget.state
                ? root.assignmentTarget.state
                : (root.assignmentTarget || {})
            if (state.assignmentId) {
                root.deleteAssignmentRequested(String(state.assignmentId))
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteDependencyDialog
        objectName: "taskDeleteDependencyDialog"
        title: "Remove Dependency"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Remove Dependency"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.dependencyTarget && root.dependencyTarget.title
            ? "Remove the dependency link to " + root.dependencyTarget.title + "?"
            : "Remove the selected dependency?"
        supportingText: "This removes the predecessor or successor link from the project plan."

        onConfirmed: {
            const state = root.dependencyTarget && root.dependencyTarget.state
                ? root.dependencyTarget.state
                : (root.dependencyTarget || {})
            if (state.dependencyId) {
                root.deleteDependencyRequested(String(state.dependencyId))
            }
        }
    }
}

