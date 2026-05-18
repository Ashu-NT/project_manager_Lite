import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Work Order"
    property var workOrderData: ({})
    property var siteOptions: []
    property var locationOptions: []
    property var systemOptions: []
    property var assetOptions: []
    property var componentOptions: []
    property var sourceTypeOptions: []
    property var sourceWorkRequestOptions: []
    property var workOrderTypeOptions: []
    property var priorityOptions: []
    property var vendorOptions: []
    property string validationMessage: ""
    readonly property bool createMode: root.modeTitle === "Create Work Order"
    readonly property bool workRequestSourceSelected: String((root.sourceTypeOptions[sourceTypeCombo.currentIndex] || { "value": "" }).value || "") === "WORK_REQUEST"
    readonly property bool showWorkRequestSourceCombo: root.createMode && root.workRequestSourceSelected
    readonly property bool showWorkRequestSourceReadonly: !root.createMode && root.workRequestSourceSelected

    signal submitted(var payload)

    modal: true
    width: 760
    height: Math.min(820, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 820)
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

    function populateFromWorkOrder() {
        const state = root.workOrderData && root.workOrderData.state ? root.workOrderData.state : (root.workOrderData || {})
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        locationCombo.currentIndex = root.indexForValue(root.locationOptions, state.locationId || "")
        systemCombo.currentIndex = root.indexForValue(root.systemOptions, state.systemId || "")
        assetCombo.currentIndex = root.indexForValue(root.assetOptions, state.assetId || "")
        componentCombo.currentIndex = root.indexForValue(root.componentOptions, state.componentId || "")
        sourceTypeCombo.currentIndex = root.indexForValue(root.sourceTypeOptions, state.sourceType || "MANUAL")
        sourceWorkRequestCombo.currentIndex = root.indexForValue(root.sourceWorkRequestOptions, state.sourceId || "")
        workOrderTypeCombo.currentIndex = root.indexForValue(root.workOrderTypeOptions, state.workOrderType || "CORRECTIVE")
        priorityCombo.currentIndex = root.indexForValue(root.priorityOptions, state.priority || "MEDIUM")
        vendorCombo.currentIndex = root.indexForValue(root.vendorOptions, state.vendorPartyId || "")
        workOrderCodeField.text = String(state.workOrderCode || "")
        manualSourceIdField.text = String(state.sourceId || "")
        readOnlySourceField.text = String(state.sourceLabel || state.sourceId || "")
        titleField.text = String(state.title || "")
        descriptionField.text = String(state.description || "")
        notesField.text = String(state.notes || "")
        requiresShutdownCheck.checked = !!state.requiresShutdown
        permitRequiredCheck.checked = !!state.permitRequired
        approvalRequiredCheck.checked = !!state.approvalRequired
        preventiveCheck.checked = !!state.isPreventive
        emergencyCheck.checked = !!state.isEmergency
        root.validationMessage = ""
    }

    function buildPayload() {
        const state = root.workOrderData && root.workOrderData.state ? root.workOrderData.state : (root.workOrderData || {})
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedLocation = root.locationOptions[locationCombo.currentIndex] || { "value": "" }
        const selectedSystem = root.systemOptions[systemCombo.currentIndex] || { "value": "" }
        const selectedAsset = root.assetOptions[assetCombo.currentIndex] || { "value": "" }
        const selectedComponent = root.componentOptions[componentCombo.currentIndex] || { "value": "" }
        const selectedSourceType = root.sourceTypeOptions[sourceTypeCombo.currentIndex] || { "value": "MANUAL" }
        const selectedSourceWorkRequest = root.sourceWorkRequestOptions[sourceWorkRequestCombo.currentIndex] || { "value": "" }
        const selectedWorkOrderType = root.workOrderTypeOptions[workOrderTypeCombo.currentIndex] || { "value": "CORRECTIVE" }
        const selectedPriority = root.priorityOptions[priorityCombo.currentIndex] || { "value": "MEDIUM" }
        const selectedVendor = root.vendorOptions[vendorCombo.currentIndex] || { "value": "" }
        const sourceTypeValue = String(selectedSourceType.value || "MANUAL")
        const sourceIdValue = sourceTypeValue === "WORK_REQUEST"
            ? (root.createMode
                ? String(selectedSourceWorkRequest.value || "")
                : String(state.sourceId || ""))
            : manualSourceIdField.text
        return {
            "workOrderId": String(state.workOrderId || ""),
            "siteId": String(selectedSite.value || ""),
            "workOrderCode": workOrderCodeField.text,
            "workOrderType": String(selectedWorkOrderType.value || "CORRECTIVE"),
            "sourceType": sourceTypeValue,
            "sourceId": sourceIdValue,
            "locationId": String(selectedLocation.value || ""),
            "systemId": String(selectedSystem.value || ""),
            "assetId": String(selectedAsset.value || ""),
            "componentId": String(selectedComponent.value || ""),
            "title": titleField.text,
            "description": descriptionField.text,
            "priority": String(selectedPriority.value || "MEDIUM"),
            "vendorPartyId": String(selectedVendor.value || ""),
            "requiresShutdown": requiresShutdownCheck.checked,
            "permitRequired": permitRequiredCheck.checked,
            "approvalRequired": approvalRequiredCheck.checked,
            "isPreventive": preventiveCheck.checked,
            "isEmergency": emergencyCheck.checked,
            "notes": notesField.text,
            "expectedVersion": Number(state.expectedVersion || 0)
        }
    }

    function submitDialog() {
        if (String((root.siteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a site before saving."
            return
        }
        if (workOrderCodeField.text.trim().length === 0) {
            root.validationMessage = "Work order code is required."
            return
        }
        if (String((root.workOrderTypeOptions[workOrderTypeCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a work-order type before saving."
            return
        }
        if (root.createMode && String((root.sourceTypeOptions[sourceTypeCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a source type before saving."
            return
        }
        if (root.createMode && root.workRequestSourceSelected && String((root.sourceWorkRequestOptions[sourceWorkRequestCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a source work request before saving."
            return
        }
        if ((!root.createMode || !root.workRequestSourceSelected) && titleField.text.trim().length === 0) {
            root.validationMessage = "Title is required."
            return
        }
        if (String((root.priorityOptions[priorityCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a priority."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromWorkOrder()

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
                text: root.createMode
                    ? "Capture execution-scope, source, and readiness details before the work order enters planning."
                    : "Update the work-order execution scope, sourcing, and readiness flags."
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
                columns: root.width > 640 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Site" }
                ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

                Label { text: "Work order code" }
                TextField { id: workOrderCodeField; Layout.fillWidth: true; placeholderText: "WO-100" }

                Label { text: "Source type" }
                ComboBox {
                    id: sourceTypeCombo
                    Layout.fillWidth: true
                    model: root.sourceTypeOptions
                    textRole: "label"
                    enabled: root.createMode
                }

                Label { text: root.workRequestSourceSelected ? "Source work request" : "Source reference" }
                StackLayout {
                    Layout.fillWidth: true
                    currentIndex: root.showWorkRequestSourceReadonly ? 2 : (root.showWorkRequestSourceCombo ? 1 : 0)

                    TextField {
                        id: manualSourceIdField
                        Layout.fillWidth: true
                        placeholderText: "Optional manual source id"
                    }

                    ComboBox {
                        id: sourceWorkRequestCombo
                        Layout.fillWidth: true
                        model: root.sourceWorkRequestOptions
                        textRole: "label"
                        enabled: root.createMode
                    }

                    TextField {
                        id: readOnlySourceField
                        Layout.fillWidth: true
                        readOnly: true
                    }
                }

                Label { text: "Work-order type" }
                ComboBox { id: workOrderTypeCombo; Layout.fillWidth: true; model: root.workOrderTypeOptions; textRole: "label" }

                Label { text: "Priority" }
                ComboBox { id: priorityCombo; Layout.fillWidth: true; model: root.priorityOptions; textRole: "label" }

                Label { text: "Location" }
                ComboBox { id: locationCombo; Layout.fillWidth: true; model: root.locationOptions; textRole: "label" }

                Label { text: "System" }
                ComboBox { id: systemCombo; Layout.fillWidth: true; model: root.systemOptions; textRole: "label" }

                Label { text: "Asset" }
                ComboBox { id: assetCombo; Layout.fillWidth: true; model: root.assetOptions; textRole: "label" }

                Label { text: "Component" }
                ComboBox { id: componentCombo; Layout.fillWidth: true; model: root.componentOptions; textRole: "label" }

                Label { text: "Vendor" }
                ComboBox { id: vendorCombo; Layout.fillWidth: true; model: root.vendorOptions; textRole: "label" }

                Label { text: "Title" }
                TextField { id: titleField; Layout.fillWidth: true; placeholderText: "Repair coupling" }
            }

            Label { text: "Description" }
            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 110
                placeholderText: "Execution intent, fault context, and repair scope."
                wrapMode: TextEdit.WordWrap
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                CheckBox { id: requiresShutdownCheck; text: "Requires shutdown" }
                CheckBox { id: permitRequiredCheck; text: "Permit required" }
                CheckBox { id: approvalRequiredCheck; text: "Approval required" }
                CheckBox { id: preventiveCheck; text: "Preventive" }
                CheckBox { id: emergencyCheck; text: "Emergency" }
            }

            Label { text: "Notes" }
            TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                placeholderText: "Planning notes, contractor context, or execution warnings."
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: root.createMode ? "Create Work Order" : "Save Changes"
            onClicked: root.submitDialog()
        }
    }
}
