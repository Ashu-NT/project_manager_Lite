pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "billingSourcePickerDialog"
    property string projectId: ""
    property string preparationId: ""
    property int preparationVersion: 0
    property var workspaceController: null
    property var options: []
    property string selectedSourceId: ""
    property string selectedSourceType: ""
    signal submitted(var payload)
    title: "Add Eligible Billing Source"
    subtitle: "Only server-authorized evidence for this preparation method is shown."
    primaryText: "Add Source"
    primaryIcon: "add"
    primaryEnabled: !root.busy && root.selectedSourceId.length > 0
    function loadSources() {
        if (!root.workspaceController) return
        const result = root.workspaceController.searchEligibleBillingSources(root.projectId, root.preparationId, searchField.text, 1, 50)
        if (!result.ok) { root.errorMessage = result.message || "Eligible sources could not be loaded."; return }
        root.options = result.items || []
    }
    function submitDialog() {
        root.submitted({ "preparationId": root.preparationId, "version": root.preparationVersion, "sourceId": root.selectedSourceId, "sourceType": root.selectedSourceType })
    }
    onOpened: { searchField.text = ""; root.selectedSourceId = ""; root.selectedSourceType = ""; root.loadSources(); searchField.forceActiveFocus() }
    Timer {
        id: searchDebounce
        interval: 280
        repeat: false
        onTriggered: root.loadSources()
    }
    AppControls.TextField {
        id: searchField
        Layout.fillWidth: true
        placeholderText: "Search eligible sources..."
        onAccepted: root.loadSources()
        onTextChanged: if (root.opened) searchDebounce.restart()
    }
    ListView {
        Layout.fillWidth: true; Layout.preferredHeight: 260; clip: true; model: root.options
        delegate: AppControls.SecondaryButton {
            required property var modelData
            width: ListView.view.width
            text: String(modelData.label || "") + " | " + String(modelData.amount || "") + " " + String(modelData.currencyCode || "")
            onClicked: { root.selectedSourceId = String(modelData.value || ""); root.selectedSourceType = String(modelData.sourceType || "") }
        }
    }
}
