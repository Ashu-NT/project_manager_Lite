import QtQuick
import Maintenance.Dialogs 1.0 as MaintenanceDialogs

Item {
    id: root

    property var workspaceController: null
    property var planFormOptions: ({})
    property var planTaskFormOptions: ({})
    property var templateFormOptions: ({})
    property var stepFormOptions: ({})

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

    function openCreatePlanDialog() {
        planDialog.openForCreate()
    }

    function openEditPlanDialog(planData) {
        planDialog.openForEdit(planData)
    }

    function openCreatePlanTaskDialog(planId) {
        planTaskDialog.openForCreate(planId)
    }

    function openEditPlanTaskDialog(planTaskData) {
        planTaskDialog.openForEdit(planTaskData)
    }

    function openCreateTaskTemplateDialog() {
        taskTemplateDialog.openForCreate()
    }

    function openEditTaskTemplateDialog(taskTemplateData) {
        taskTemplateDialog.openForEdit(taskTemplateData)
    }

    function openCreateTaskStepDialog(taskTemplateId) {
        taskStepDialog.openForCreate(taskTemplateId)
    }

    function openEditTaskStepDialog(taskStepData) {
        taskStepDialog.openForEdit(taskStepData)
    }

    MaintenanceDialogs.PreventivePlanEditorDialog {
        id: planDialog
        formOptions: root.planFormOptions

        onSaveRequested: function(payload) {
            if (payload.planId) {
                root._handleResult(planDialog, root.workspaceController.updatePlan(payload))
            } else {
                root._handleResult(planDialog, root.workspaceController.createPlan(payload))
            }
        }
    }

    MaintenanceDialogs.PreventivePlanTaskEditorDialog {
        id: planTaskDialog
        formOptions: root.planTaskFormOptions

        onSaveRequested: function(payload) {
            if (payload.planTaskId) {
                root._handleResult(planTaskDialog, root.workspaceController.updatePlanTask(payload))
            } else {
                root._handleResult(planTaskDialog, root.workspaceController.createPlanTask(payload))
            }
        }
    }

    MaintenanceDialogs.TaskTemplateEditorDialog {
        id: taskTemplateDialog
        formOptions: root.templateFormOptions

        onSaveRequested: function(payload) {
            if (payload.taskTemplateId) {
                root._handleResult(taskTemplateDialog, root.workspaceController.updateTaskTemplate(payload))
            } else {
                root._handleResult(taskTemplateDialog, root.workspaceController.createTaskTemplate(payload))
            }
        }
    }

    MaintenanceDialogs.TaskStepTemplateEditorDialog {
        id: taskStepDialog
        formOptions: root.stepFormOptions

        onSaveRequested: function(payload) {
            if (payload.taskStepTemplateId) {
                root._handleResult(taskStepDialog, root.workspaceController.updateTaskStep(payload))
            } else {
                root._handleResult(taskStepDialog, root.workspaceController.createTaskStep(payload))
            }
        }
    }
}
