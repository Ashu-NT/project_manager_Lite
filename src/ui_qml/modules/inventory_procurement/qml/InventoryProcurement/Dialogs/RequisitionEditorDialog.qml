import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Requisition"
    property var siteOptions: []
    property var storeroomOptions: []
    property var requisitionData: ({})

    signal submitted(var payload)

    width: 720
    title: root.modeTitle
    subtitle: root.modeTitle === "Create Requisition"
        ? "Capture internal supply demand against a real site and storeroom before the approval and sourcing flow starts."
        : "Update the requisition scope, priority, and delivery target before sourcing begins."
    primaryText: root.modeTitle === "Create Requisition" ? "Create Requisition" : "Save Changes"
    primaryIcon: root.modeTitle === "Create Requisition" ? "add" : "save"
    onAccepted: root.submitDialog()
    onRejected: root.close()

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

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 620 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Site" }
        AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

        AppControls.Label { text: "Storeroom" }
        AppControls.ComboBox { id: storeroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

        AppControls.Label { text: "Priority" }
        AppControls.ComboBox { id: priorityCombo; Layout.fillWidth: true; model: root.priorityOptions; textRole: "label" }

        AppControls.Label { text: "Purpose" }
        AppControls.TextField { id: purposeField; Layout.fillWidth: true; placeholderText: "Why is the supply needed?" }

        AppControls.Label { text: "Needed by (YYYY-MM-DD)" }
        AppControls.DateField { id: neededByDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }
    }

    AppControls.Label {
        text: "Notes"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 100
        wrapMode: TextEdit.WordWrap
        placeholderText: "Scope, urgency, or requester context."
    }
}
