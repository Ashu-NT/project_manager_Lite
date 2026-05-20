import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create System"
    property var recordState: ({})
    property var siteOptions: []
    property var locationOptions: []
    property var parentSystemOptions: []
    property var statusOptions: []
    property var criticalityOptions: []
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 720
    height: Math.min(780, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 780)
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
        parentSystemCombo.currentIndex = root.indexForValue(root.parentSystemOptions, state.parentSystemId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        criticalityCombo.currentIndex = root.indexForValue(root.criticalityOptions, state.criticality || "MEDIUM")
        systemCodeField.text = String(state.systemCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        systemTypeField.text = String(state.systemType || "")
        notesField.text = String(state.notes || "")
        activeCheck.checked = state.isActive === undefined ? true : !!state.isActive
        root.validationMessage = ""
    }

    function buildPayload() {
        const state = root.recordState || {}
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedLocation = root.locationOptions[locationCombo.currentIndex] || { "value": "" }
        const selectedParent = root.parentSystemOptions[parentSystemCombo.currentIndex] || { "value": "" }
        const selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "ACTIVE" }
        const selectedCriticality = root.criticalityOptions[criticalityCombo.currentIndex] || { "value": "MEDIUM" }
        return {
            "systemId": String(state.systemId || ""),
            "siteId": String(selectedSite.value || ""),
            "locationId": String(selectedLocation.value || ""),
            "systemCode": systemCodeField.text,
            "name": nameField.text,
            "description": descriptionField.text,
            "parentSystemId": String(selectedParent.value || ""),
            "systemType": systemTypeField.text,
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
        if (systemCodeField.text.trim().length === 0) {
            root.validationMessage = "System code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "System name is required."
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
                text: "Capture system hierarchy and lifecycle state for maintenance planning scope."
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

                Label { text: "System code" }
                TextField { id: systemCodeField; Layout.fillWidth: true; placeholderText: "SYS-100" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Packaging Line" }

                Label { text: "Location" }
                ComboBox { id: locationCombo; Layout.fillWidth: true; model: root.locationOptions; textRole: "label" }

                Label { text: "Parent system" }
                ComboBox { id: parentSystemCombo; Layout.fillWidth: true; model: root.parentSystemOptions; textRole: "label" }

                Label { text: "System type" }
                TextField { id: systemTypeField; Layout.fillWidth: true; placeholderText: "LINE" }

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

            CheckBox { id: activeCheck; text: "Active system" }

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
            text: root.modeTitle === "Create System" ? "Create System" : "Save Changes"
            iconName: root.modeTitle === "Create System" ? "add" : "save"
            onClicked: root.submitDialog()
        }
    }
}
