import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Location"
    property var recordState: ({})
    property var siteOptions: []
    property var parentLocationOptions: []
    property var statusOptions: []
    property var criticalityOptions: []
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

    function populateFromRecord() {
        const state = root.recordState || {}
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        parentLocationCombo.currentIndex = root.indexForValue(root.parentLocationOptions, state.parentLocationId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        criticalityCombo.currentIndex = root.indexForValue(root.criticalityOptions, state.criticality || "MEDIUM")
        locationCodeField.text = String(state.locationCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        locationTypeField.text = String(state.locationType || "")
        notesField.text = String(state.notes || "")
        activeCheck.checked = state.isActive === undefined ? true : !!state.isActive
        root.validationMessage = ""
    }

    function buildPayload() {
        const state = root.recordState || {}
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedParent = root.parentLocationOptions[parentLocationCombo.currentIndex] || { "value": "" }
        const selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "ACTIVE" }
        const selectedCriticality = root.criticalityOptions[criticalityCombo.currentIndex] || { "value": "MEDIUM" }
        return {
            "locationId": String(state.locationId || ""),
            "siteId": String(selectedSite.value || ""),
            "locationCode": locationCodeField.text,
            "name": nameField.text,
            "description": descriptionField.text,
            "parentLocationId": String(selectedParent.value || ""),
            "locationType": locationTypeField.text,
            "criticality": String(selectedCriticality.value || "MEDIUM"),
            "status": String(selectedStatus.value || "ACTIVE"),
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
        if (locationCodeField.text.trim().length === 0) {
            root.validationMessage = "Location code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Location name is required."
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
                text: "Capture site location hierarchy, lifecycle state, and scope notes for maintenance anchors."
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

                Label { text: "Location code" }
                TextField { id: locationCodeField; Layout.fillWidth: true; placeholderText: "LOC-100" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Production Area A" }

                Label { text: "Parent location" }
                ComboBox { id: parentLocationCombo; Layout.fillWidth: true; model: root.parentLocationOptions; textRole: "label" }

                Label { text: "Location type" }
                TextField { id: locationTypeField; Layout.fillWidth: true; placeholderText: "PRODUCTION" }

                Label { text: "Criticality" }
                ComboBox { id: criticalityCombo; Layout.fillWidth: true; model: root.criticalityOptions; textRole: "label" }

                Label { text: "Lifecycle status" }
                ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }
            }

            Label { text: "Description" }
            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                wrapMode: TextEdit.WordWrap
            }

            CheckBox { id: activeCheck; text: "Active location" }

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
            onClicked: root.close()
        }
        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: root.modeTitle === "Create Location" ? "Create Location" : "Save Changes"
            onClicked: root.submitDialog()
        }
    }
}
