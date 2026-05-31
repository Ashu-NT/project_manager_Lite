import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var formOptions: ({})
    property bool editing: false
    property var initialState: ({})
    property string selectedTaskTemplateId: ""

    signal saveRequested(var payload)

    title:       root.editing ? "Edit Task Step" : "New Task Step"
    subtitle:    "Configure a step within the maintenance task template."
    primaryText: root.editing ? "Save Changes" : "Add Step"
    primaryIcon: root.editing ? "save" : "add"
    width: 620

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

    function openForCreate(taskTemplateId) {
        root.editing = false
        root.selectedTaskTemplateId = String(taskTemplateId || "")
        root.initialState = ({
            "stepNumber": "",
            "sortOrder": "",
            "instruction": "",
            "expectedResult": "",
            "hintLevel": "",
            "hintText": "",
            "requiresConfirmation": false,
            "requiresMeasurement": false,
            "requiresPhoto": false,
            "measurementUnit": "",
            "isActive": true,
            "notes": ""
        })
        loadState()
        open()
    }

    function openForEdit(taskStepData) {
        root.editing = true
        root.initialState = taskStepData && taskStepData.state ? taskStepData.state : (taskStepData || {})
        root.selectedTaskTemplateId = String(root.initialState.taskTemplateId || "")
        loadState()
        open()
    }

    function loadState() {
        const state = root.initialState || {}
        hintLevelCombo.currentIndex = comboIndex(hintLevelCombo.model, state.hintLevel)
        stepNumberField.text = String(state.stepNumber || "")
        sortOrderField.text = String(state.sortOrder || "")
        instructionArea.text = String(state.instruction || "")
        expectedResultArea.text = String(state.expectedResult || "")
        hintTextArea.text = String(state.hintText || "")
        measurementUnitField.text = String(state.measurementUnit || "")
        notesArea.text = String(state.notes || "")
        requiresConfirmationCheck.checked = Boolean(state.requiresConfirmation)
        requiresMeasurementCheck.checked = Boolean(state.requiresMeasurement)
        requiresPhotoCheck.checked = Boolean(state.requiresPhoto)
        activeCheck.checked = state.isActive === undefined ? true : Boolean(state.isActive)
    }

    function buildPayload() {
        const state = root.initialState || {}
        return {
            "taskStepTemplateId": root.editing ? String(state.taskStepTemplateId || "") : "",
            "taskTemplateId": root.editing ? String(state.taskTemplateId || root.selectedTaskTemplateId || "") : root.selectedTaskTemplateId,
            "stepNumber": stepNumberField.text,
            "sortOrder": sortOrderField.text,
            "instruction": instructionArea.text,
            "expectedResult": expectedResultArea.text,
            "hintLevel": comboValue(hintLevelCombo),
            "hintText": hintTextArea.text,
            "requiresConfirmation": requiresConfirmationCheck.checked,
            "requiresMeasurement": requiresMeasurementCheck.checked,
            "requiresPhoto": requiresPhotoCheck.checked,
            "measurementUnit": measurementUnitField.text,
            "isActive": activeCheck.checked,
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

        AppControls.Label { text: "Step Number" }
        AppControls.TextField { id: stepNumberField; Layout.fillWidth: true; placeholderText: "1" }

        AppControls.Label { text: "Sort Order" }
        AppControls.TextField { id: sortOrderField; Layout.fillWidth: true; placeholderText: "1" }

        AppControls.Label { text: "Hint Level" }
        AppControls.ComboBox { id: hintLevelCombo; Layout.fillWidth: true; model: root.optionsFor("hintLevelOptions"); textRole: "label" }

        AppControls.Label { text: "Measurement Unit" }
        AppControls.TextField { id: measurementUnitField; Layout.fillWidth: true; placeholderText: "mm / H / PSI" }
    }

    AppControls.CheckBox { id: requiresConfirmationCheck; text: "Requires confirmation" }
    AppControls.CheckBox { id: requiresMeasurementCheck; text: "Requires measurement capture" }
    AppControls.CheckBox { id: requiresPhotoCheck; text: "Requires photo capture" }
    AppControls.CheckBox { id: activeCheck; text: "Active" }

    AppControls.Label { text: "Instruction" }
    AppControls.TextArea {
        id: instructionArea
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        placeholderText: "Describe the step instruction."
        wrapMode: TextEdit.WordWrap
    }

    AppControls.Label { text: "Expected Result" }
    AppControls.TextArea {
        id: expectedResultArea
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        placeholderText: "Describe the expected result."
        wrapMode: TextEdit.WordWrap
    }

    AppControls.Label { text: "Hint Text" }
    AppControls.TextArea {
        id: hintTextArea
        Layout.fillWidth: true
        Layout.preferredHeight: 80
        placeholderText: "Optional escalation or operator hint."
        wrapMode: TextEdit.WordWrap
    }

    AppControls.Label { text: "Notes" }
    AppControls.TextArea {
        id: notesArea
        Layout.fillWidth: true
        Layout.preferredHeight: 80
        placeholderText: "Optional authoring notes."
        wrapMode: TextEdit.WordWrap
    }
}
