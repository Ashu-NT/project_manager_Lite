import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
AppControls.CenteredDialog {
    id: root

    property var formOptions: ({})
    property bool editing: false
    property var initialState: ({})
    property string selectedPlanId: ""

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 680
    height: 620
    title: root.editing ? "Edit Plan Task" : "New Plan Task"

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

    standardButtons: Dialog.Ok | Dialog.Cancel
    onAccepted: root.saveRequested(buildPayload())

    contentItem: ScrollView {
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 12
                rowSpacing: 12

                Label { text: "Task Template" }
                ComboBox { id: taskTemplateCombo; Layout.fillWidth: true; model: root.optionsFor("taskTemplateOptions"); textRole: "label" }

                Label { text: "Sequence" }
                TextField { id: sequenceNoField; Layout.fillWidth: true; placeholderText: "1" }

                Label { text: "Trigger Scope" }
                ComboBox { id: triggerScopeCombo; Layout.fillWidth: true; model: root.optionsFor("triggerScopeOptions"); textRole: "label" }

                Label { text: "Trigger Mode Override" }
                ComboBox { id: triggerModeOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("triggerModeOptions"); textRole: "label" }

                Label { text: "Calendar Unit Override" }
                ComboBox { id: calendarUnitOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("calendarFrequencyUnitOptions"); textRole: "label" }

                Label { text: "Calendar Value Override" }
                TextField { id: calendarValueOverrideField; Layout.fillWidth: true; placeholderText: "Optional" }

                Label { text: "Sensor Override" }
                ComboBox { id: sensorOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("sensorOptions"); textRole: "label" }

                Label { text: "Sensor Threshold Override" }
                TextField { id: sensorThresholdOverrideField; Layout.fillWidth: true; placeholderText: "Optional" }

                Label { text: "Sensor Direction Override" }
                ComboBox { id: sensorDirectionOverrideCombo; Layout.fillWidth: true; model: root.optionsFor("sensorDirectionOptions"); textRole: "label" }

                Label { text: "Assigned Team" }
                TextField { id: assignedTeamField; Layout.fillWidth: true; placeholderText: "MECH-A" }

                Label { text: "Estimated Minutes Override" }
                TextField { id: estimateField; Layout.fillWidth: true; placeholderText: "45" }
            }

            CheckBox { id: mandatoryCheck; text: "Mandatory" }

            Label { text: "Notes" }
            TextArea {
                id: notesArea
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                placeholderText: "Override notes, trigger comments, or crew instructions."
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}

