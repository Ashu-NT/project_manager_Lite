import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Asset"
    property var recordState: ({})
    property var siteOptions: []
    property var locationOptions: []
    property var systemOptions: []
    property var parentAssetOptions: []
    property var statusOptions: []
    property var criticalityOptions: []
    property var manufacturerOptions: []
    property var supplierOptions: []
    property var workspaceController: null
    property string assetCode: ""

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Asset"
        ? "Capture asset identity, anchor context, lifecycle state, and maintenance strategy."
        : "Update the asset record, anchor context, and maintenance strategy."
    primaryText:  root.modeTitle === "Create Asset" ? "Create Asset" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Asset" ? "add" : "save"
    width: 820

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
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        locationCombo.currentIndex = root.indexForValue(root.locationOptions, state.locationId || "")
        systemCombo.currentIndex = root.indexForValue(root.systemOptions, state.systemId || "")
        parentAssetCombo.currentIndex = root.indexForValue(root.parentAssetOptions, state.parentAssetId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        criticalityCombo.currentIndex = root.indexForValue(root.criticalityOptions, state.criticality || "MEDIUM")
        manufacturerCombo.currentIndex = root.indexForValue(root.manufacturerOptions, state.manufacturerPartyId || "")
        supplierCombo.currentIndex = root.indexForValue(root.supplierOptions, state.supplierPartyId || "")
        root.assetCode = String(state.assetCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        assetTypeField.text = String(state.assetType || "")
        assetCategoryField.text = String(state.assetCategory || "")
        modelNumberField.text = String(state.modelNumber || "")
        serialNumberField.text = String(state.serialNumber || "")
        replacementCostField.text = String(state.replacementCost || "")
        maintenanceStrategyField.text = String(state.maintenanceStrategy || "")
        serviceLevelField.text = String(state.serviceLevel || "")
        notesField.text = String(state.notes || "")
        activeCheck.checked = state.isActive === undefined ? true : !!state.isActive
        shutdownCheck.checked = !!state.requiresShutdownForMajorWork
        root.errorMessage = ""
    }

    function buildPayload() {
        const state = root.recordState || {}
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedLocation = root.locationOptions[locationCombo.currentIndex] || { "value": "" }
        const selectedSystem = root.systemOptions[systemCombo.currentIndex] || { "value": "" }
        const selectedParentAsset = root.parentAssetOptions[parentAssetCombo.currentIndex] || { "value": "" }
        const selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "ACTIVE" }
        const selectedCriticality = root.criticalityOptions[criticalityCombo.currentIndex] || { "value": "MEDIUM" }
        const selectedManufacturer = root.manufacturerOptions[manufacturerCombo.currentIndex] || { "value": "" }
        const selectedSupplier = root.supplierOptions[supplierCombo.currentIndex] || { "value": "" }
        return {
            "assetId": String(state.assetId || ""),
            "siteId": String(selectedSite.value || ""),
            "locationId": String(selectedLocation.value || ""),
            "systemId": String(selectedSystem.value || ""),
            "parentAssetId": String(selectedParentAsset.value || ""),
            "assetCode": root.assetCode,
            "name": nameField.text,
            "description": descriptionField.text,
            "assetType": assetTypeField.text,
            "assetCategory": assetCategoryField.text,
            "criticality": String(selectedCriticality.value || "MEDIUM"),
            "status": String(selectedStatus.value || "ACTIVE"),
            "manufacturerPartyId": String(selectedManufacturer.value || ""),
            "supplierPartyId": String(selectedSupplier.value || ""),
            "modelNumber": modelNumberField.text,
            "serialNumber": serialNumberField.text,
            "replacementCost": replacementCostField.text,
            "maintenanceStrategy": maintenanceStrategyField.text,
            "serviceLevel": serviceLevelField.text,
            "requiresShutdownForMajorWork": shutdownCheck.checked,
            "isActive": activeCheck.checked,
            "notes": notesField.text,
            "expectedVersion": Number(state.expectedVersion || 0)
        }
    }

    function submitDialog() {
        if (String((root.siteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a site before saving."
            return
        }
        if (String((root.locationOptions[locationCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a location before saving."
            return
        }
        if (root.assetCode.trim().length === 0) {
            root.errorMessage = "Asset code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Asset name is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 700 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Site" }
        AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

        AppControls.Label { text: "Location" }
        AppControls.ComboBox { id: locationCombo; Layout.fillWidth: true; model: root.locationOptions; textRole: "label" }

        AppControls.Label { text: "System" }
        AppControls.ComboBox { id: systemCombo; Layout.fillWidth: true; model: root.systemOptions; textRole: "label" }

        AppControls.Label { text: "Parent asset" }
        AppControls.ComboBox { id: parentAssetCombo; Layout.fillWidth: true; model: root.parentAssetOptions; textRole: "label" }

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            label: "Asset code"
            value: root.assetCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            onValueEdited: function(code) { root.assetCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("asset", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.assetCode = suggested
                    }
                }
            }
        }

        AppControls.Label { text: "Name" }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Conveyor 100" }

        AppControls.Label { text: "Asset type" }
        AppControls.TextField { id: assetTypeField; Layout.fillWidth: true; placeholderText: "CONVEYOR" }

        AppControls.Label { text: "Category" }
        AppControls.TextField { id: assetCategoryField; Layout.fillWidth: true; placeholderText: "ROTATING" }

        AppControls.Label { text: "Criticality" }
        AppControls.ComboBox { id: criticalityCombo; Layout.fillWidth: true; model: root.criticalityOptions; textRole: "label" }

        AppControls.Label { text: "Lifecycle status" }
        AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }

        AppControls.Label { text: "Manufacturer" }
        AppControls.ComboBox { id: manufacturerCombo; Layout.fillWidth: true; model: root.manufacturerOptions; textRole: "label" }

        AppControls.Label { text: "Supplier" }
        AppControls.ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }

        AppControls.Label { text: "Model number" }
        AppControls.TextField { id: modelNumberField; Layout.fillWidth: true }

        AppControls.Label { text: "Serial number" }
        AppControls.TextField { id: serialNumberField; Layout.fillWidth: true }

        AppControls.Label { text: "Replacement cost" }
        AppControls.TextField { id: replacementCostField; Layout.fillWidth: true; placeholderText: "2500.00" }

        AppControls.Label { text: "Maintenance strategy" }
        AppControls.TextField { id: maintenanceStrategyField; Layout.fillWidth: true; placeholderText: "Condition-based" }

        AppControls.Label { text: "Service level" }
        AppControls.TextField { id: serviceLevelField; Layout.fillWidth: true; placeholderText: "Tier 1" }
    }

    AppControls.Label { text: "Description" }
    AppControls.TextArea {
        id: descriptionField
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        wrapMode: TextEdit.WordWrap
    }

    Flow {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd
        AppControls.CheckBox { id: activeCheck; text: "Active asset" }
        AppControls.CheckBox { id: shutdownCheck; text: "Requires shutdown for major work" }
    }

    AppControls.Label { text: "Notes" }
    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        wrapMode: TextEdit.WordWrap
    }
}
