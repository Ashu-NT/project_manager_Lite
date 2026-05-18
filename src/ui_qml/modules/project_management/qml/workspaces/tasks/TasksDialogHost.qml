import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property string selectedProjectId: ""
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
            payload.projectId = String(state.projectId || root.selectedProjectId || "")
            if (state.taskId) {
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

        resourceOptions: root.assignmentOptions

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

        onSubmitted: function(payload) {
            root.setAssignmentHoursRequested(payload)
            assignmentHoursDialog.close()
        }
    }

    ProjectManagementDialogs.TaskDependencyEditorDialog {
        id: dependencyEditorDialog

        taskOptions: root.dependencyTaskOptions
        dependencyTypeOptions: root.dependencyTypeOptions

        onSubmitted: function(payload) {
            root.createDependencyRequested(payload)
            dependencyEditorDialog.close()
        }
    }

    ProjectManagementDialogs.TaskCollaborationComposerDialog {
        id: collaborationComposerDialog

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

    Dialog {
        id: deleteDialog

        modal: true
        title: "Delete Task"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: root.deleteTarget && root.deleteTarget.title
                    ? "Delete " + root.deleteTarget.title + " and its dependent planning data?"
                    : "Delete the selected task and its dependent planning data?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This action removes the task record plus related dependencies, assignments, and linked planning items."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            const state = root.deleteTarget && root.deleteTarget.state
                ? root.deleteTarget.state
                : (root.deleteTarget || {})
            if (state.taskId) {
                root.deleteRequested(String(state.taskId))
            }
        }
    }

    Dialog {
        id: bulkDeleteDialog

        modal: true
        title: "Bulk Delete Tasks"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: "Delete " + String((root.bulkDeleteTargetIds || []).length) + " selected tasks and their dependencies/assignments?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This action cannot be undone."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            root.bulkDeleteRequested(root.bulkDeleteTargetIds || [])
        }
    }

    Dialog {
        id: deleteAssignmentDialog

        modal: true
        title: "Remove Assignment"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: root.assignmentTarget && root.assignmentTarget.title
                    ? "Remove " + root.assignmentTarget.title + " from the selected task?"
                    : "Remove the selected assignment?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This removes the assignment from the task but does not delete the underlying resource."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            const state = root.assignmentTarget && root.assignmentTarget.state
                ? root.assignmentTarget.state
                : (root.assignmentTarget || {})
            if (state.assignmentId) {
                root.deleteAssignmentRequested(String(state.assignmentId))
            }
        }
    }

    Dialog {
        id: deleteDependencyDialog

        modal: true
        title: "Remove Dependency"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: root.dependencyTarget && root.dependencyTarget.title
                    ? "Remove the dependency link to " + root.dependencyTarget.title + "?"
                    : "Remove the selected dependency?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This removes the predecessor or successor link from the project plan."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            const state = root.dependencyTarget && root.dependencyTarget.state
                ? root.dependencyTarget.state
                : (root.dependencyTarget || {})
            if (state.dependencyId) {
                root.deleteDependencyRequested(String(state.dependencyId))
            }
        }
    }
}
