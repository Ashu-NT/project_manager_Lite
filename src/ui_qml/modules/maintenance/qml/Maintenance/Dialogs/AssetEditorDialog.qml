import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
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
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 820
    height: Math.min(900, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 900)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

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
        assetCodeField.text = String(state.assetCode || "")
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
        root.validationMessage = ""
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
            "assetCode": assetCodeField.text,
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
            root.validationMessage = "Choose a site before saving."
            return
        }
        if (String((root.locationOptions[locationCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a location before saving."
            return
        }
        if (assetCodeField.text.trim().length === 0) {
            root.validationMessage = "Asset code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Asset name is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromRecord()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: Flickable {
        id: dialogFlickable
        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout
            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "Capture asset identity, anchor context, lifecycle state, and maintenance strategy."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 700 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Site" }
                ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

                Label { text: "Location" }
                ComboBox { id: locationCombo; Layout.fillWidth: true; model: root.locationOptions; textRole: "label" }

                Label { text: "System" }
                ComboBox { id: systemCombo; Layout.fillWidth: true; model: root.systemOptions; textRole: "label" }

                Label { text: "Parent asset" }
                ComboBox { id: parentAssetCombo; Layout.fillWidth: true; model: root.parentAssetOptions; textRole: "label" }

                Label { text: "Asset code" }
                TextField { id: assetCodeField; Layout.fillWidth: true; placeholderText: "AST-100" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Conveyor 100" }

                Label { text: "Asset type" }
                TextField { id: assetTypeField; Layout.fillWidth: true; placeholderText: "CONVEYOR" }

                Label { text: "Category" }
                TextField { id: assetCategoryField; Layout.fillWidth: true; placeholderText: "ROTATING" }

                Label { text: "Criticality" }
                ComboBox { id: criticalityCombo; Layout.fillWidth: true; model: root.criticalityOptions; textRole: "label" }

                Label { text: "Lifecycle status" }
                ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }

                Label { text: "Manufacturer" }
                ComboBox { id: manufacturerCombo; Layout.fillWidth: true; model: root.manufacturerOptions; textRole: "label" }

                Label { text: "Supplier" }
                ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }

                Label { text: "Model number" }
                TextField { id: modelNumberField; Layout.fillWidth: true }

                Label { text: "Serial number" }
                TextField { id: serialNumberField; Layout.fillWidth: true }

                Label { text: "Replacement cost" }
                TextField { id: replacementCostField; Layout.fillWidth: true; placeholderText: "2500.00" }

                Label { text: "Maintenance strategy" }
                TextField { id: maintenanceStrategyField; Layout.fillWidth: true; placeholderText: "Condition-based" }

                Label { text: "Service level" }
                TextField { id: serviceLevelField; Layout.fillWidth: true; placeholderText: "Tier 1" }
            }

            Label { text: "Description" }
            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                wrapMode: TextEdit.WordWrap
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd
                CheckBox { id: activeCheck; text: "Active asset" }
                CheckBox { id: shutdownCheck; text: "Requires shutdown for major work" }
            }

            Label { text: "Notes" }
            TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm
        Item { Layout.fillWidth: true }
        Button { text: "Cancel"; onClicked: root.close() }
        AppControls.PrimaryButton {
            text: root.modeTitle === "Create Asset" ? "Create Asset" : "Save Changes"
            onClicked: root.submitDialog()
        }
    }
}
