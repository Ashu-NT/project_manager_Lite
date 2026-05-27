import QtQuick
import Maintenance.Dialogs 1.0 as MaintenanceDialogs

Item {
    id: root

    property var planFormOptions: ({})
    property var planTaskFormOptions: ({})
    property var templateFormOptions: ({})
    property var stepFormOptions: ({})

    signal createPlanRequested(var payload)
    signal updatePlanRequested(var payload)
    signal createPlanTaskRequested(var payload)
    signal updatePlanTaskRequested(var payload)
    signal createTaskTemplateRequested(var payload)
    signal updateTaskTemplateRequested(var payload)
    signal createTaskStepRequested(var payload)
    signal updateTaskStepRequested(var payload)

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
                root.updatePlanRequested(payload)
            } else {
                root.createPlanRequested(payload)
            }
        }
    }

    MaintenanceDialogs.PreventivePlanTaskEditorDialog {
        id: planTaskDialog
        formOptions: root.planTaskFormOptions

        onSaveRequested: function(payload) {
            if (payload.planTaskId) {
                root.updatePlanTaskRequested(payload)
            } else {
                root.createPlanTaskRequested(payload)
            }
        }
    }

    MaintenanceDialogs.TaskTemplateEditorDialog {
        id: taskTemplateDialog
        formOptions: root.templateFormOptions

        onSaveRequested: function(payload) {
            if (payload.taskTemplateId) {
                root.updateTaskTemplateRequested(payload)
            } else {
                root.createTaskTemplateRequested(payload)
            }
        }
    }

    MaintenanceDialogs.TaskStepTemplateEditorDialog {
        id: taskStepDialog
        formOptions: root.stepFormOptions

        onSaveRequested: function(payload) {
            if (payload.taskStepTemplateId) {
                root.updateTaskStepRequested(payload)
            } else {
                root.createTaskStepRequested(payload)
            }
        }
    }
}

