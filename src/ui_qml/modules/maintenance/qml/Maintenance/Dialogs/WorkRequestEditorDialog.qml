import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Work Request"
    property var workRequestData: ({})
    property var siteOptions: []
    property var locationOptions: []
    property var systemOptions: []
    property var assetOptions: []
    property var componentOptions: []
    property var sourceTypeOptions: []
    property var priorityOptions: []
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 720
    height: Math.min(760, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 760)
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

    function populateFromWorkRequest() {
        const state = root.workRequestData && root.workRequestData.state ? root.workRequestData.state : (root.workRequestData || {})
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        locationCombo.currentIndex = root.indexForValue(root.locationOptions, state.locationId || "")
        systemCombo.currentIndex = root.indexForValue(root.systemOptions, state.systemId || "")
        assetCombo.currentIndex = root.indexForValue(root.assetOptions, state.assetId || "")
        componentCombo.currentIndex = root.indexForValue(root.componentOptions, state.componentId || "")
        sourceTypeCombo.currentIndex = root.indexForValue(root.sourceTypeOptions, state.sourceType || "")
        priorityCombo.currentIndex = root.indexForValue(root.priorityOptions, state.priority || "MEDIUM")
        workRequestCodeField.text = String(state.workRequestCode || "")
        sourceIdField.text = String(state.sourceId || "")
        requestTypeField.text = String(state.requestType || "")
        titleField.text = String(state.title || "")
        descriptionField.text = String(state.description || "")
        failureSymptomField.text = String(state.failureSymptomCode || "")
        safetyRiskField.text = String(state.safetyRiskLevel || "")
        productionImpactField.text = String(state.productionImpactLevel || "")
        notesField.text = String(state.notes || "")
        root.validationMessage = ""
    }

    function buildPayload() {
        const state = root.workRequestData && root.workRequestData.state ? root.workRequestData.state : (root.workRequestData || {})
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedLocation = root.locationOptions[locationCombo.currentIndex] || { "value": "" }
        const selectedSystem = root.systemOptions[systemCombo.currentIndex] || { "value": "" }
        const selectedAsset = root.assetOptions[assetCombo.currentIndex] || { "value": "" }
        const selectedComponent = root.componentOptions[componentCombo.currentIndex] || { "value": "" }
        const selectedSourceType = root.sourceTypeOptions[sourceTypeCombo.currentIndex] || { "value": "" }
        const selectedPriority = root.priorityOptions[priorityCombo.currentIndex] || { "value": "MEDIUM" }
        return {
            "workRequestId": String(state.workRequestId || ""),
            "workRequestCode": workRequestCodeField.text,
            "siteId": String(selectedSite.value || ""),
            "locationId": String(selectedLocation.value || ""),
            "systemId": String(selectedSystem.value || ""),
            "assetId": String(selectedAsset.value || ""),
            "componentId": String(selectedComponent.value || ""),
            "sourceType": String(selectedSourceType.value || ""),
            "sourceId": sourceIdField.text,
            "requestType": requestTypeField.text,
            "title": titleField.text,
            "description": descriptionField.text,
            "priority": String(selectedPriority.value || "MEDIUM"),
            "failureSymptomCode": failureSymptomField.text,
            "safetyRiskLevel": safetyRiskField.text,
            "productionImpactLevel": productionImpactField.text,
            "notes": notesField.text,
            "expectedVersion": Number(state.expectedVersion || 0)
        }
    }

    function submitDialog() {
        if (String((root.siteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a site before saving."
            return
        }
        if (String((root.sourceTypeOptions[sourceTypeCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a source type before saving."
            return
        }
        if (requestTypeField.text.trim().length === 0) {
            root.validationMessage = "Request type is required."
            return
        }
        if (titleField.text.trim().length === 0) {
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

    onOpened: root.populateFromWorkRequest()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
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
                text: root.modeTitle === "Create Work Request"
                    ? "Capture intake details before the request is triaged or converted into execution planning."
                    : "Update the work-request intake record, asset scope, and triage context."
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
                columns: root.width > 620 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Site" }
                ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

                Label { text: "Work request code" }
                TextField { id: workRequestCodeField; Layout.fillWidth: true; placeholderText: "WR-100" }

                Label { text: "Source type" }
                ComboBox { id: sourceTypeCombo; Layout.fillWidth: true; model: root.sourceTypeOptions; textRole: "label" }

                Label { text: "Source id" }
                TextField { id: sourceIdField; Layout.fillWidth: true; placeholderText: "Origin ticket or request id" }

                Label { text: "Request type" }
                TextField { id: requestTypeField; Layout.fillWidth: true; placeholderText: "CORRECTIVE / BREAKDOWN / INSPECTION" }

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

                Label { text: "Title" }
                TextField { id: titleField; Layout.fillWidth: true; placeholderText: "Seal leak observed on transfer pump" }

                Label { text: "Failure symptom code" }
                TextField { id: failureSymptomField; Layout.fillWidth: true; placeholderText: "Optional symptom code" }

                Label { text: "Safety risk" }
                TextField { id: safetyRiskField; Layout.fillWidth: true; placeholderText: "LOW / MEDIUM / HIGH" }

                Label { text: "Production impact" }
                TextField { id: productionImpactField; Layout.fillWidth: true; placeholderText: "LOW / MEDIUM / HIGH" }
            }

            Label { text: "Description" }
            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                placeholderText: "Problem details, symptoms, and request context."
                wrapMode: TextEdit.WordWrap
            }

            Label { text: "Notes" }
            TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                placeholderText: "Triage notes or requester follow-up context."
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
            text: root.modeTitle === "Create Work Request" ? "Create Request" : "Save Changes"
            onClicked: root.submitDialog()
        }
    }
}
