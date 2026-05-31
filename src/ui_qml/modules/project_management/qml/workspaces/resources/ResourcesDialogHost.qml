import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var workspaceController: null
    property var workerTypeOptions: []
    property var categoryOptions: []
    property var employeeOptions: []
    property var editTarget: ({})
    property var deleteTarget: ({})

    signal deleteRequested(string resourceId)
    signal removeSkillRequested(string skillId)
    signal removeCertificationRequested(string certId)

    function _handleResult(dialog, result) {
        if (!result || result.success) {
            dialog.close()
        } else {
            dialog.errorMessage = result.error || "An unexpected error occurred."
        }
    }

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "workerType": "EXTERNAL",
                "costType": "LABOR",
                "isActive": true,
                "capacityPercent": "100.0"
            }
        }
        editorDialog.modeTitle = "Create Resource"
        editorDialog.resourceData = root.editTarget
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openEditDialog(resourceData) {
        root.editTarget = resourceData || ({})
        editorDialog.modeTitle = "Edit Resource"
        editorDialog.resourceData = root.editTarget
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openDeleteDialog(resourceData) {
        root.deleteTarget = resourceData || ({})
        deleteDialog.open()
    }

    function openAddSkillDialog() {
        skillEditorDialog.errorMessage = ""
        skillEditorDialog.open()
    }

    function openAddCertificationDialog() {
        certEditorDialog.errorMessage = ""
        certEditorDialog.open()
    }

    ProjectManagementDialogs.ResourceSkillEditorDialog {
        id: skillEditorDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            var result = root.workspaceController.addSkill(payload)
            root._handleResult(skillEditorDialog, result)
        }
    }

    ProjectManagementDialogs.ResourceCertificationEditorDialog {
        id: certEditorDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            var result = root.workspaceController.addCertification(payload)
            root._handleResult(certEditorDialog, result)
        }
    }

    ProjectManagementDialogs.ResourceEditorDialog {
        id: editorDialog

        workerTypeOptions: root.workerTypeOptions
        categoryOptions: root.categoryOptions
        employeeOptions: root.employeeOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            var result
            if (state.resourceId) {
                payload.resourceId = state.resourceId
                payload.expectedVersion = state.version
                result = root.workspaceController.updateResource(payload)
            } else {
                result = root.workspaceController.createResource(payload)
            }
            root._handleResult(editorDialog, result)
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteDialog
        title: "Delete Resource"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Resource"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.deleteTarget && root.deleteTarget.title
            ? "Delete " + root.deleteTarget.title + " and its related assignments?"
            : "Delete the selected resource and its related assignments?"
        supportingText: "This action removes the resource record and any PM assignments or linked allocation history that depends on it."

        onConfirmed: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.resourceId) {
                root.deleteRequested(String(state.resourceId))
            }
        }
    }
}
