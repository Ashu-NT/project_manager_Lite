import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var formOptions: ({})
    property bool editing: false
    property var initialState: ({})
    property string selectedPlanId: ""

    signal saveRequested(var payload)

    title:       root.editing ? "Edit Plan Task" : "New Plan Task"
    subtitle:    "Configure task parameters within the preventive maintenance plan."
    primaryText: root.editing ? "Save Changes" : "Add Task"
    primaryIcon: root.editing ? "save" : "add"
    width: 680

    onAccepted: root.saveRequested(buildPayload())
    onRejected: root.close()

    function optionsFor(key) {
        return root.formOptions && root.formOptions[key] ? root.formOptions[key] : []
    }

    function comboIndex(options, value) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(value || "")) {
                return index
            }
        }
        return options.length > 0 ? 0 : -1
    }

    function comboValue(comboBox) {
        if (!comboBox.model || comboBox.currentIndex < 0 || comboBox.currentIndex >= comboBox.model.length) {
            return ""
        }
        return String(comboBox.model[comboBox.currentIndex].value || "")
    }

    function openForCreate(planId) {
        root.editing = false
        root.selectedPlanId = String(planId || "")
        root.initialState = ({
            "taskTemplateId": "",
            "triggerScope": "INHERIT_PLAN",
            "triggerModeOverride": "",
            "calendarFrequencyUnitOverride": "",
            "calendarFrequencyValueOverride": "",
            "sensorIdOverride": "",
            "sensorThresholdOverride": "",
            "sensorDirectionOverride": "",
            "sequenceNo": "",
            "isMandatory": true,
            "defaultAssignedTeamId": "",
            "estimatedMinutesOverride": "",
            "notes": ""
        })
        loadState()
        open()
    }

    function openForEdit(planTaskData) {
        root.editing = true
        root.initialState = planTaskData && planTaskData.state ? planTaskData.state : (planTaskData || {})
        root.selectedPlanId = String(root.initialState.planId || "")
        loadState()
        open()
    }

    function loadState() {
        const state = root.initialState || {}
        taskTemplateCombo.currentIndex = comboIndex(taskTemplateCombo.model, state.taskTemplateId)
        triggerScopeCombo.currentIndex = comboIndex(triggerScopeCombo.model, state.triggerScope)
        triggerModeOverrideCombo.currentIndex = comboIndex(triggerModeOverrideCombo.model, state.triggerModeOverride)
        calendarUnitOverrideCombo.currentIndex = comboIndex(calendarUnitOverrideCombo.model, state.calendarFrequencyUnitOverride)
        sensorOverrideCombo.currentIndex = comboIndex(sensorOverrideCombo.model, state.sensorIdOverride)
        sensorDirectionOverrideCombo.currentIndex = comboIndex(sensorDirectionOverrideCombo.model, state.sensorDirectionOverride)
        sequenceNoField.text = String(state.sequenceNo || "")
        calendarValueOverrideField.text = String(state.calendarFrequencyValueOverride || "")
        sensorThresholdOverrideField.text = String(state.sensorThresholdOverride || "")
        assignedTeamField.text = String(state.defaultAssignedTeamId || "")
        estimateField.text = String(state.estimatedMinutesOverride || "")
        notesArea.text = String(state.notes || "")
        mandatoryCheck.checked = state.isMandatory === undefined ? true : Boolean(state.isMandatory)
    }

    function buildPayload() {
        const state = root.initialState || {}
        return {
            "planTaskId": root.editing ? String(state.planTaskId || "") : "",
            "planId": root.editing ? String(state.planId || root.selectedPlanId || "") : root.selectedPlanId,
            "taskTemplateId": comboValue(taskTemplateCombo),
            "triggerScope": comboValue(triggerScopeCombo),
            "triggerModeOverride": comboValue(triggerModeOverrideCombo),
            "calendarFrequencyUnitOverride": comboValue(calendarUnitOverrideCombo),
            "calendarFrequencyValueOverride": calendarValueOverrideField.text,
            "sensorIdOverride": comboValue(sensorOverrideCombo),
            "sensorThresholdOverride": sensorThresholdOverrideField.text,
            "sensorDirectionOverride": comboValue(sensorDirectionOverrideCombo),
            "sequenceNo": sequenceNoField.text,
            "isMandatory": mandatoryCheck.checked,
            "defaultAssignedTeamId": assignedTeamField.text,
            "estimatedMinutesOverride": estimateField.text,
            "notes": notesArea.text,
            "expectedVersion": root.editing ? Number(state.expectedVersion || 0) : 0
        }
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Task Template"
            AppControls.ComboBox { id: taskTemplateCombo; Layout.fillWidth: true; model: root.optionsFor("taskTemplateOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sequence"
            AppControls.TextField { id: sequenceNoField; Layout.fillWidth: true; placeholderText: "1" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Trigger Scope"
            AppControls.ComboBox { id: triggerScopeCombo; Layout.fillWidth: true; model: root.optionsFor("triggerScopeOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Trigger Mode Override"
            AppControls.ComboBox { id: triggerModeOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("triggerModeOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Calendar Unit Override"
            AppControls.ComboBox { id: calendarUnitOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("calendarFrequencyUnitOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Calendar Value Override"
            AppControls.TextField { id: calendarValueOverrideField; Layout.fillWidth: true; placeholderText: "Optional" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor Override"
            AppControls.ComboBox { id: sensorOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("sensorOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor Threshold Override"
            AppControls.TextField { id: sensorThresholdOverrideField; Layout.fillWidth: true; placeholderText: "Optional" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor Direction Override"
            AppControls.ComboBox { id: sensorDirectionOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("sensorDirectionOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Assigned Team"
            AppControls.TextField { id: assignedTeamField; Layout.fillWidth: true; placeholderText: "MECH-A" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Estimated Minutes Override"
            AppControls.TextField { id: estimateField; Layout.fillWidth: true; placeholderText: "45" }
        }
    }

    AppControls.CheckBox { id: mandatoryCheck; text: "Mandatory" }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"
        AppControls.TextArea {
            id: notesArea
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            placeholderText: "Override notes, trigger comments, or crew instructions."
            wrapMode: TextEdit.WordWrap
        }
    }
}
