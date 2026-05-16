import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    property var formOptions: ({})
    property bool editing: false
    property var initialState: ({})

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 640
    height: 620
    title: root.editing ? "Edit Task Template" : "New Task Template"

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

    function openForCreate() {
        root.editing = false
        root.initialState = ({
            "taskTemplateCode": "",
            "name": "",
            "description": "",
            "maintenanceType": "PREVENTIVE",
            "revisionNo": "1",
            "templateStatus": "DRAFT",
            "estimatedMinutes": "",
            "requiredSkill": "",
            "requiresShutdown": false,
            "requiresPermit": false,
            "isActive": true,
            "notes": ""
        })
        loadState()
        open()
    }

    function openForEdit(taskTemplateData) {
        root.editing = true
        root.initialState = taskTemplateData && taskTemplateData.state ? taskTemplateData.state : (taskTemplateData || {})
        loadState()
        open()
    }

    function loadState() {
        const state = root.initialState || {}
        maintenanceTypeCombo.currentIndex = comboIndex(maintenanceTypeCombo.model, state.maintenanceType)
        templateStatusCombo.currentIndex = comboIndex(templateStatusCombo.model, state.templateStatus)
        taskTemplateCodeField.text = String(state.taskTemplateCode || "")
        nameField.text = String(state.name || "")
        descriptionArea.text = String(state.description || "")
        revisionNoField.text = String(state.revisionNo || "1")
        estimatedMinutesField.text = String(state.estimatedMinutes || "")
        requiredSkillField.text = String(state.requiredSkill || "")
        requiresShutdownCheck.checked = Boolean(state.requiresShutdown)
        requiresPermitCheck.checked = Boolean(state.requiresPermit)
        activeCheck.checked = state.isActive === undefined ? true : Boolean(state.isActive)
        notesArea.text = String(state.notes || "")
    }

    function buildPayload() {
        const state = root.initialState || {}
        return {
            "taskTemplateId": root.editing ? String(state.taskTemplateId || "") : "",
            "taskTemplateCode": taskTemplateCodeField.text,
            "name": nameField.text,
            "description": descriptionArea.text,
            "maintenanceType": comboValue(maintenanceTypeCombo),
            "revisionNo": revisionNoField.text,
            "templateStatus": comboValue(templateStatusCombo),
            "estimatedMinutes": estimatedMinutesField.text,
            "requiredSkill": requiredSkillField.text,
            "requiresShutdown": requiresShutdownCheck.checked,
            "requiresPermit": requiresPermitCheck.checked,
            "isActive": activeCheck.checked,
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

                Label { text: "Template Code" }
                TextField { id: taskTemplateCodeField; Layout.fillWidth: true; placeholderText: "PM-SEAL-CHECK" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Seal Inspection Route" }

                Label { text: "Maintenance Type" }
                ComboBox { id: maintenanceTypeCombo; Layout.fillWidth: true; model: root.optionsFor("maintenanceTypeOptions"); textRole: "label" }

                Label { text: "Revision" }
                TextField { id: revisionNoField; Layout.fillWidth: true; placeholderText: "1" }

                Label { text: "Template Status" }
                ComboBox { id: templateStatusCombo; Layout.fillWidth: true; model: root.optionsFor("statusOptions"); textRole: "label" }

                Label { text: "Estimated Minutes" }
                TextField { id: estimatedMinutesField; Layout.fillWidth: true; placeholderText: "45" }

                Label { text: "Required Skill" }
                TextField { id: requiredSkillField; Layout.fillWidth: true; placeholderText: "Mechanical" }
            }

            CheckBox { id: requiresShutdownCheck; text: "Requires shutdown" }
            CheckBox { id: requiresPermitCheck; text: "Requires permit" }
            CheckBox { id: activeCheck; text: "Active" }

            Label { text: "Description" }
            TextArea {
                id: descriptionArea
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                placeholderText: "Reusable template description, maintenance context, and route scope."
                wrapMode: TextEdit.WordWrap
            }

            Label { text: "Notes" }
            TextArea {
                id: notesArea
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                placeholderText: "Revision notes or template-governance context."
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}
