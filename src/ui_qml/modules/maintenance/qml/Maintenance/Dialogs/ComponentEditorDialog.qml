import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Component"
    property var recordState: ({})
    property var assetOptions: []
    property var parentComponentOptions: []
    property var statusOptions: []
    property var manufacturerOptions: []
    property var supplierOptions: []
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 760
    height: Math.min(860, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 860)
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
        assetCombo.currentIndex = root.indexForValue(root.assetOptions, state.assetId || "")
        parentComponentCombo.currentIndex = root.indexForValue(root.parentComponentOptions, state.parentComponentId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        manufacturerCombo.currentIndex = root.indexForValue(root.manufacturerOptions, state.manufacturerPartyId || "")
        supplierCombo.currentIndex = root.indexForValue(root.supplierOptions, state.supplierPartyId || "")
        componentCodeField.text = String(state.componentCode || "")
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
        root.validationMessage = ""
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
            "componentCode": componentCodeField.text,
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
            root.validationMessage = "Choose an asset before saving."
            return
        }
        if (componentCodeField.text.trim().length === 0) {
            root.validationMessage = "Component code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Component name is required."
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
                text: "Capture component identity, supplier context, and lifecycle state under the selected asset."
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
                columns: root.width > 680 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Asset" }
                ComboBox { id: assetCombo; Layout.fillWidth: true; model: root.assetOptions; textRole: "label" }

                Label { text: "Parent component" }
                ComboBox { id: parentComponentCombo; Layout.fillWidth: true; model: root.parentComponentOptions; textRole: "label" }

                Label { text: "Component code" }
                TextField { id: componentCodeField; Layout.fillWidth: true; placeholderText: "CMP-100" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Drive Motor" }

                Label { text: "Component type" }
                TextField { id: componentTypeField; Layout.fillWidth: true; placeholderText: "MOTOR" }

                Label { text: "Lifecycle status" }
                ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }

                Label { text: "Manufacturer" }
                ComboBox { id: manufacturerCombo; Layout.fillWidth: true; model: root.manufacturerOptions; textRole: "label" }

                Label { text: "Supplier" }
                ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }

                Label { text: "Manufacturer part number" }
                TextField { id: manufacturerPartNumberField; Layout.fillWidth: true }

                Label { text: "Supplier part number" }
                TextField { id: supplierPartNumberField; Layout.fillWidth: true }

                Label { text: "Model number" }
                TextField { id: modelNumberField; Layout.fillWidth: true }

                Label { text: "Serial number" }
                TextField { id: serialNumberField; Layout.fillWidth: true }

                Label { text: "Expected life hours" }
                TextField { id: expectedLifeHoursField; Layout.fillWidth: true; placeholderText: "12000" }

                Label { text: "Expected life cycles" }
                TextField { id: expectedLifeCyclesField; Layout.fillWidth: true; placeholderText: "500000" }
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
                CheckBox { id: activeCheck; text: "Active component" }
                CheckBox { id: criticalCheck; text: "Critical component" }
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
        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }
        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: root.modeTitle === "Create Component" ? "Create Component" : "Save Changes"
            iconName: root.modeTitle === "Create Component" ? "add" : "save"
            onClicked: root.submitDialog()
        }
    }
}
