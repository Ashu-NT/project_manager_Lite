import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Component"
    property var recordState: ({})
    property var assetOptions: []
    property var parentComponentOptions: []
    property var statusOptions: []
    property var manufacturerOptions: []
    property var supplierOptions: []
    property var workspaceController: null
    property string componentCode: ""

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Component"
        ? "Capture component identity, supplier context, and lifecycle state under the selected asset."
        : "Update the component record, supplier context, and lifecycle state."
    primaryText:  root.modeTitle === "Create Component" ? "Create Component" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Component" ? "add" : "save"
    width: 760

    onOpened:   root.populateFromRecord()
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromRecord() {
        const state = root.recordState || {}
        assetCombo.currentIndex = root.indexForValue(root.assetOptions, state.assetId || "")
        parentComponentCombo.currentIndex = root.indexForValue(root.parentComponentOptions, state.parentComponentId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        manufacturerCombo.currentIndex = root.indexForValue(root.manufacturerOptions, state.manufacturerPartyId || "")
        supplierCombo.currentIndex = root.indexForValue(root.supplierOptions, state.supplierPartyId || "")
        root.componentCode = String(state.componentCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        componentTypeField.text = String(state.componentType || "")
        manufacturerPartNumberField.text = String(state.manufacturerPartNumber || "")
        supplierPartNumberField.text = String(state.supplierPartNumber || "")
        modelNumberField.text = String(state.modelNumber || "")
        serialNumberField.text = String(state.serialNumber || "")
        expectedLifeHoursField.text = String(state.expectedLifeHours || "")
        expectedLifeCyclesField.text = String(state.expectedLifeCycles || "")
        notesField.text = String(state.notes || "")
        activeCheck.checked = state.isActive === undefined ? true : !!state.isActive
        criticalCheck.checked = !!state.isCriticalComponent
        root.errorMessage = ""
    }

    function buildPayload() {
        const state = root.recordState || {}
        const selectedAsset = root.assetOptions[assetCombo.currentIndex] || { "value": "" }
        const selectedParent = root.parentComponentOptions[parentComponentCombo.currentIndex] || { "value": "" }
        const selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "ACTIVE" }
        const selectedManufacturer = root.manufacturerOptions[manufacturerCombo.currentIndex] || { "value": "" }
        const selectedSupplier = root.supplierOptions[supplierCombo.currentIndex] || { "value": "" }
        return {
            "componentId": String(state.componentId || ""),
            "assetId": String(selectedAsset.value || ""),
            "componentCode": root.componentCode,
            "name": nameField.text,
            "description": descriptionField.text,
            "parentComponentId": String(selectedParent.value || ""),
            "componentType": componentTypeField.text,
            "status": String(selectedStatus.value || "ACTIVE"),
            "manufacturerPartyId": String(selectedManufacturer.value || ""),
            "supplierPartyId": String(selectedSupplier.value || ""),
            "manufacturerPartNumber": manufacturerPartNumberField.text,
            "supplierPartNumber": supplierPartNumberField.text,
            "modelNumber": modelNumberField.text,
            "serialNumber": serialNumberField.text,
            "expectedLifeHours": expectedLifeHoursField.text,
            "expectedLifeCycles": expectedLifeCyclesField.text,
            "isCriticalComponent": criticalCheck.checked,
            "isActive": activeCheck.checked,
            "notes": notesField.text,
            "expectedVersion": Number(state.expectedVersion || 0)
        }
    }

    function submitDialog() {
        if (String((root.assetOptions[assetCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose an asset before saving."
            return
        }
        if (root.componentCode.trim().length === 0) {
            root.errorMessage = "Component code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Component name is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 680 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Asset"
            required: true
            AppControls.ComboBox { id: assetCombo; Layout.fillWidth: true; model: root.assetOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Parent component"
            AppControls.ComboBox { id: parentComponentCombo; Layout.fillWidth: true; model: root.parentComponentOptions; textRole: "label" }
        }

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            label: "Component code"
            value: root.componentCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            onValueEdited: function(code) { root.componentCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("component", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.componentCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Name"
            required: true
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Drive Motor" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Component type"
            AppControls.TextField { id: componentTypeField; Layout.fillWidth: true; placeholderText: "MOTOR" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Lifecycle status"
            AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Manufacturer"
            AppControls.ComboBox { id: manufacturerCombo; Layout.fillWidth: true; model: root.manufacturerOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Supplier"
            AppControls.ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Manufacturer part number"
            AppControls.TextField { id: manufacturerPartNumberField; Layout.fillWidth: true }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Supplier part number"
            AppControls.TextField { id: supplierPartNumberField; Layout.fillWidth: true }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Model number"
            AppControls.TextField { id: modelNumberField; Layout.fillWidth: true }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Serial number"
            AppControls.TextField { id: serialNumberField; Layout.fillWidth: true }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Expected life hours"
            AppControls.TextField { id: expectedLifeHoursField; Layout.fillWidth: true; placeholderText: "12000" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Expected life cycles"
            AppControls.TextField { id: expectedLifeCyclesField; Layout.fillWidth: true; placeholderText: "500000" }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionField
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            wrapMode: TextEdit.WordWrap
        }
    }

    Flow {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd
        AppControls.CheckBox { id: activeCheck; text: "Active component" }
        AppControls.CheckBox { id: criticalCheck; text: "Critical component" }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"
        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            wrapMode: TextEdit.WordWrap
        }
    }
}
