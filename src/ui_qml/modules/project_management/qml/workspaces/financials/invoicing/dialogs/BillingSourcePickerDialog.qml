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
    property int sourcePage: 1
    property int sourceTotal: 0
    readonly property int sourcePageSize: 50
    property string selectedSourceId: ""
    property string selectedSourceType: ""
    signal submitted(var payload)
    title: "Add Eligible Billing Source"
    subtitle: "Only server-authorized evidence for this preparation method is shown."
    primaryText: "Add Source"
    primaryIcon: "add"
    initialFocusTarget: searchField
    primaryEnabled: !root.busy && root.selectedSourceId.length > 0
    function clearSelection() {
        root.selectedSourceId = ""
        root.selectedSourceType = ""
    }
    function loadSources() {
        searchDebounce.stop()
        root.clearSelection()
        root.options = []
        root.sourceTotal = 0
        if (!root.opened || !root.workspaceController) return
        const result = root.workspaceController.searchEligibleBillingSources(root.projectId, root.preparationId, searchField.text, root.sourcePage, root.sourcePageSize)
        if (!result || !result.ok) { root.errorMessage = (result && result.message) || "Eligible sources could not be loaded."; return }
        root.errorMessage = ""
        root.options = result.items || []
        root.sourcePage = Number(result.page || 1)
        root.sourceTotal = Number(result.total || 0)
    }
    function submitDialog() {
        if (!root.primaryEnabled) return
        root.submitted({ "preparationId": root.preparationId, "version": root.preparationVersion, "sourceId": root.selectedSourceId, "sourceType": root.selectedSourceType })
    }
    onOpened: { searchField.text = ""; root.sourcePage = 1; root.loadSources(); searchField.forceActiveFocus() }
    onClosed: { searchDebounce.stop(); root.clearSelection(); root.options = []; root.sourceTotal = 0 }
    onPreparationIdChanged: { searchDebounce.stop(); root.clearSelection(); root.options = [] }
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
        onAccepted: { root.sourcePage = 1; root.loadSources() }
        onTextChanged: {
            root.clearSelection()
            root.sourcePage = 1
            if (root.opened) searchDebounce.restart()
        }
    }
    ListView {
        Layout.fillWidth: true; Layout.preferredHeight: 260; clip: true; model: root.options
        delegate: AppControls.SecondaryButton {
            required property var modelData
            width: ListView.view.width
            checkable: true
            checked: root.selectedSourceId === String(modelData.value || "")
            text: String(modelData.label || "") + " | " + String(modelData.amount || "") + " " + String(modelData.currencyCode || "")
            onClicked: { root.selectedSourceId = String(modelData.value || ""); root.selectedSourceType = String(modelData.sourceType || "") }
        }
    }
    AppWidgets.TablePaginationBar {
        Layout.fillWidth: true
        currentPage: root.sourcePage
        pageSize: root.sourcePageSize
        totalItems: root.sourceTotal
        busy: root.busy
        onPageRequested: function(page) { root.sourcePage = page; root.loadSources() }
    }
}
