import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Requisition"
    property var siteOptions: []
    property var storeroomOptions: []
    property var requisitionData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 720
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromRequisition() {
        var state = root.requisitionData && root.requisitionData.state ? root.requisitionData.state : (root.requisitionData || {})
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.requestingSiteId || "")
        storeroomCombo.currentIndex = root.indexForValue(root.storeroomOptions, state.requestingStoreroomId || "")
        priorityCombo.currentIndex = root.indexForValue(priorityOptions, state.priority || "NORMAL")
        purposeField.text = String(state.purpose || root.requisitionData.description || "")
        neededByDateField.text = String(state.neededByDateIso || "")
        notesField.text = String(state.notes || "")
        root.validationMessage = ""
    }

    function buildPayload() {
        var selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        var selectedStoreroom = root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }
        var selectedPriority = priorityOptions[priorityCombo.currentIndex] || { "value": "NORMAL" }
        return {
            "requestingSiteId": String(selectedSite.value || ""),
            "requestingStoreroomId": String(selectedStoreroom.value || ""),
            "priority": String(selectedPriority.value || "NORMAL"),
            "purpose": purposeField.text,
            "neededByDate": neededByDateField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.siteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a site before saving the requisition."
            return
        }
        if (String((root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a storeroom before saving the requisition."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    readonly property var priorityOptions: [
        { "value": "LOW", "label": "Low" },
        { "value": "NORMAL", "label": "Normal" },
        { "value": "HIGH", "label": "High" },
        { "value": "URGENT", "label": "Urgent" }
    ]

    onOpened: root.populateFromRequisition()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Capture internal supply demand against a real site and storeroom before the approval and sourcing flow starts."
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

            Label { text: "Storeroom" }
            ComboBox { id: storeroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

            Label { text: "Priority" }
            ComboBox { id: priorityCombo; Layout.fillWidth: true; model: root.priorityOptions; textRole: "label" }

            Label { text: "Purpose" }
            TextField { id: purposeField; Layout.fillWidth: true; placeholderText: "Why is the supply needed?" }

            Label { text: "Needed by (YYYY-MM-DD)" }
            TextField { id: neededByDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }
        }

        Label {
            text: "Notes"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            wrapMode: TextEdit.WordWrap
            placeholderText: "Scope, urgency, or requester context."
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
            text: "Save"
            iconName: "save"
            onClicked: root.submitDialog()
        }
    }
}
