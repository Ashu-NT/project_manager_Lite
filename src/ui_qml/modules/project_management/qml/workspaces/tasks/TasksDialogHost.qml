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
    property var editTarget: ({})
    property var progressTarget: ({})
    property var deleteTarget: ({})
    property var assignmentTarget: ({})
    property var dependencyTarget: ({})

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
        editorDialog.modeTitle = "Edit Task"
        editorDialog.taskData = root.editTarget
        editorDialog.open()
    }

    function openProgressDialog(taskData) {
        root.progressTarget = taskData || ({})
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

    ProjectManagementDialogs.TaskEditorDialog {
        id: editorDialog

        statusOptions: root.statusOptions

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

    Dialog {
        id: deleteDialog

        modal: true
        title: "Delete Task"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
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
        id: deleteAssignmentDialog

        modal: true
        title: "Remove Assignment"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
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
            border.color: Theme.AppTheme.border
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
