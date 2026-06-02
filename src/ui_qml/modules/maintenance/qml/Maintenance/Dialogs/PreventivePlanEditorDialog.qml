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

    signal saveRequested(var payload)

    title:       root.editing ? "Edit Preventive Plan" : "New Preventive Plan"
    subtitle:    "Configure preventive maintenance plan schedule and generation settings."
    primaryText: root.editing ? "Save Changes" : "Create Plan"
    primaryIcon: root.editing ? "save" : "add"
    width: 760

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

    function openForCreate() {
        root.editing = false
        root.initialState = ({
            "siteId": "",
            "planCode": "",
            "name": "",
            "assetId": "",
            "componentId": "",
            "systemId": "",
            "description": "",
            "status": "ACTIVE",
            "planType": "PREVENTIVE",
            "priority": "MEDIUM",
            "triggerMode": "CALENDAR",
            "schedulePolicy": "FIXED",
            "calendarFrequencyUnit": "WEEKLY",
            "calendarFrequencyValue": "1",
            "generationHorizonCount": "3",
            "generationLeadValue": "0",
            "generationLeadUnit": "DAYS",
            "sensorId": "",
            "sensorThreshold": "",
            "sensorDirection": "GREATER_OR_EQUAL",
            "sensorResetRule": "",
            "requiresShutdown": false,
            "approvalRequired": false,
            "autoGenerateWorkOrder": false,
            "isActive": true,
            "notes": ""
        })
        loadState()
        open()
    }

    function openForEdit(planData) {
        root.editing = true
        root.initialState = planData && planData.state ? planData.state : (planData || {})
        loadState()
        open()
    }

    function loadState() {
        const state = root.initialState || {}
        siteCombo.currentIndex = comboIndex(siteCombo.model, state.siteId)
        assetCombo.currentIndex = comboIndex(assetCombo.model, state.assetId)
        componentCombo.currentIndex = comboIndex(componentCombo.model, state.componentId)
        systemCombo.currentIndex = comboIndex(systemCombo.model, state.systemId)
        statusCombo.currentIndex = comboIndex(statusCombo.model, state.status)
        planTypeCombo.currentIndex = comboIndex(planTypeCombo.model, state.planType)
        priorityCombo.currentIndex = comboIndex(priorityCombo.model, state.priority)
        triggerModeCombo.currentIndex = comboIndex(triggerModeCombo.model, state.triggerMode)
        schedulePolicyCombo.currentIndex = comboIndex(schedulePolicyCombo.model, state.schedulePolicy)
        calendarUnitCombo.currentIndex = comboIndex(calendarUnitCombo.model, state.calendarFrequencyUnit)
        generationLeadUnitCombo.currentIndex = comboIndex(generationLeadUnitCombo.model, state.generationLeadUnit)
        sensorCombo.currentIndex = comboIndex(sensorCombo.model, state.sensorId)
        sensorDirectionCombo.currentIndex = comboIndex(sensorDirectionCombo.model, state.sensorDirection)
        planCodeField.text = String(state.planCode || "")
        nameField.text = String(state.name || "")
        descriptionArea.text = String(state.description || "")
        calendarValueField.text = String(state.calendarFrequencyValue || "")
        generationHorizonField.text = String(state.generationHorizonCount || "")
        generationLeadValueField.text = String(state.generationLeadValue || "")
        sensorThresholdField.text = String(state.sensorThreshold || "")
        sensorResetRuleField.text = String(state.sensorResetRule || "")
        notesArea.text = String(state.notes || "")
        requiresShutdownCheck.checked = Boolean(state.requiresShutdown)
        approvalRequiredCheck.checked = Boolean(state.approvalRequired)
        autoGenerateCheck.checked = Boolean(state.autoGenerateWorkOrder)
        activeCheck.checked = state.isActive === undefined ? true : Boolean(state.isActive)
    }

    function buildPayload() {
        const state = root.initialState || {}
        return {
            "planId": root.editing ? String(state.planId || "") : "",
            "siteId": comboValue(siteCombo),
            "planCode": planCodeField.text,
            "name": nameField.text,
            "assetId": comboValue(assetCombo),
            "componentId": comboValue(componentCombo),
            "systemId": comboValue(systemCombo),
            "description": descriptionArea.text,
            "status": comboValue(statusCombo),
            "planType": comboValue(planTypeCombo),
            "priority": comboValue(priorityCombo),
            "triggerMode": comboValue(triggerModeCombo),
            "schedulePolicy": comboValue(schedulePolicyCombo),
            "calendarFrequencyUnit": comboValue(calendarUnitCombo),
            "calendarFrequencyValue": calendarValueField.text,
            "generationHorizonCount": generationHorizonField.text,
            "generationLeadValue": generationLeadValueField.text,
            "generationLeadUnit": comboValue(generationLeadUnitCombo),
            "sensorId": comboValue(sensorCombo),
            "sensorThreshold": sensorThresholdField.text,
            "sensorDirection": comboValue(sensorDirectionCombo),
            "sensorResetRule": sensorResetRuleField.text,
            "requiresShutdown": requiresShutdownCheck.checked,
            "approvalRequired": approvalRequiredCheck.checked,
            "autoGenerateWorkOrder": autoGenerateCheck.checked,
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

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Site"
            AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.optionsFor("siteOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Plan Code"
            AppControls.TextField { id: planCodeField; Layout.fillWidth: true; placeholderText: "PM-100" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Name"
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Monthly inspection route" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Asset"
            AppControls.ComboBox { id: assetCombo; Layout.fillWidth: true; model: root.optionsFor("assetOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Component"
            AppControls.ComboBox { id: componentCombo; Layout.fillWidth: true; model: root.optionsFor("componentOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "System"
            AppControls.ComboBox { id: systemCombo; Layout.fillWidth: true; model: root.optionsFor("systemOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Status"
            AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.optionsFor("statusOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Plan Type"
            AppControls.ComboBox { id: planTypeCombo; Layout.fillWidth: true; model: root.optionsFor("planTypeOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Priority"
            AppControls.ComboBox { id: priorityCombo; Layout.fillWidth: true; model: root.optionsFor("priorityOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Trigger Mode"
            AppControls.ComboBox { id: triggerModeCombo; Layout.fillWidth: true; model: root.optionsFor("triggerModeOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Schedule Policy"
            AppControls.ComboBox { id: schedulePolicyCombo; Layout.fillWidth: true; model: root.optionsFor("schedulePolicyOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Calendar Unit"
            AppControls.ComboBox { id: calendarUnitCombo; Layout.fillWidth: true; model: root.optionsFor("calendarFrequencyUnitOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Calendar Value"
            AppControls.TextField { id: calendarValueField; Layout.fillWidth: true; placeholderText: "1" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Generation Horizon"
            AppControls.TextField { id: generationHorizonField; Layout.fillWidth: true; placeholderText: "3" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Generation Lead"
            RowLayout {
                Layout.fillWidth: true
                AppControls.TextField { id: generationLeadValueField; Layout.fillWidth: true; placeholderText: "0" }
                AppControls.ComboBox { id: generationLeadUnitCombo; Layout.preferredWidth: 180; model: root.optionsFor("generationLeadUnitOptions"); textRole: "label" }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor"
            AppControls.ComboBox { id: sensorCombo; Layout.fillWidth: true; model: root.optionsFor("sensorOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor Threshold"
            AppControls.TextField { id: sensorThresholdField; Layout.fillWidth: true; placeholderText: "1200" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor Direction"
            AppControls.ComboBox { id: sensorDirectionCombo; Layout.fillWidth: true; model: root.optionsFor("sensorDirectionOptions"); textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Sensor Reset Rule"
            AppControls.TextField { id: sensorResetRuleField; Layout.fillWidth: true; placeholderText: "manual reset" }
        }
    }

    AppControls.CheckBox { id: requiresShutdownCheck; text: "Requires shutdown" }
    AppControls.CheckBox { id: approvalRequiredCheck; text: "Approval required" }
    AppControls.CheckBox { id: autoGenerateCheck; text: "Auto-generate work order" }
    AppControls.CheckBox { id: activeCheck; text: "Active" }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionArea
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            placeholderText: "Plan context, trigger notes, and anchor scope."
            wrapMode: TextEdit.WordWrap
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"
        AppControls.TextArea {
            id: notesArea
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            placeholderText: "Planner notes, constraints, or governance context."
            wrapMode: TextEdit.WordWrap
        }
    }
}
