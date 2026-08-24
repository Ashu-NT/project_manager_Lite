import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var workspaceController: null
    property var workerTypeOptions: []
    property var kindOptions: []
    property var categoryOptions: []
    property var employeeOptions: []
    property var departmentOptions: []
    property var siteOptions: []
    property var editTarget: ({})
    property var lifecycleTarget: ({})

    signal deactivateRequested(string resourceId, int expectedVersion)
    signal reactivateRequested(string resourceId, int expectedVersion)
    signal removeSkillRequested(string skillId)
    signal removeCertificationRequested(string certId)

    function _handleResult(dialog, result) {
        if (result && result.ok === true) {
            dialog.close()
        } else {
            dialog.errorMessage = String(result && result.message
                ? result.message : "The resource could not be saved.")
                + (result && result.conflict === true
                    ? " Close this dialog, reload the resource, and apply your changes again." : "")
        }
    }

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "workerType": "EXTERNAL",
                "kind": "PERSON",
                "costType": "LABOR",
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

    function openLifecycleDialog(resourceData) {
        root.lifecycleTarget = resourceData || ({})
        lifecycleDialog.open()
    }

    function openAddSkillDialog() {
        skillEditorDialog.modeTitle = "Add Skill"
        skillEditorDialog.skillData = ({})
        skillEditorDialog.errorMessage = ""
        skillEditorDialog.open()
    }

    function openEditSkillDialog(skillData) {
        skillEditorDialog.modeTitle = "Edit Skill"
        skillEditorDialog.skillData = skillData || ({})
        skillEditorDialog.errorMessage = ""
        skillEditorDialog.open()
    }

    function openAddCertificationDialog() {
        certEditorDialog.modeTitle = "Add Certification"
        certEditorDialog.certificationData = ({})
        certEditorDialog.errorMessage = ""
        certEditorDialog.open()
    }

    function openEditCertificationDialog(certificationData) {
        certEditorDialog.modeTitle = "Edit Certification"
        certEditorDialog.certificationData = certificationData || ({})
        certEditorDialog.errorMessage = ""
        certEditorDialog.open()
    }

    ResourceSkillEditorDialog {
        id: skillEditorDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            var result = skillEditorDialog.modeTitle === "Add Skill"
                ? root.workspaceController.addSkill(payload)
                : root.workspaceController.updateSkill(payload)
            root._handleResult(skillEditorDialog, result)
        }
    }

    ResourceCertificationEditorDialog {
        id: certEditorDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            var result = certEditorDialog.modeTitle === "Add Certification"
                ? root.workspaceController.addCertification(payload)
                : root.workspaceController.updateCertification(payload)
            root._handleResult(certEditorDialog, result)
        }
    }

    ResourceEditorDialog {
        id: editorDialog

        workspaceController: root.workspaceController
        workerTypeOptions: root.workerTypeOptions
        kindOptions: root.kindOptions
        categoryOptions: root.categoryOptions
        employeeOptions: root.employeeOptions
        departmentOptions: root.departmentOptions
        siteOptions: root.siteOptions
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
        id: lifecycleDialog
        readonly property var targetState: root.lifecycleTarget && root.lifecycleTarget.state
            ? root.lifecycleTarget.state : (root.lifecycleTarget || {})
        readonly property bool targetIsActive: targetState.isActive !== false
        title: targetIsActive ? "Deactivate Resource" : "Reactivate Resource"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: targetIsActive ? "Deactivate" : "Reactivate"
        confirmIcon: targetIsActive ? "close" : "approve"
        confirmDanger: targetIsActive
        message: (targetIsActive ? "Deactivate " : "Reactivate ")
            + String(root.lifecycleTarget.title || "this resource") + "?"
        supportingText: targetIsActive
            ? "Historical assignments and time remain intact. The resource will no longer be available for new planning."
            : "The resource will become available for planning again."

        onConfirmed: {
            var state = lifecycleDialog.targetState
            if (state.resourceId) {
                if (lifecycleDialog.targetIsActive)
                    root.deactivateRequested(String(state.resourceId), Number(state.version || 0))
                else
                    root.reactivateRequested(String(state.resourceId), Number(state.version || 0))
            }
        }
    }
}
