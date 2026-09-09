pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "rateCardEditorDialog"
    property string mode: "create"
    property string projectId: ""
    property var rateCard: null
    signal submitted(var payload)
    readonly property bool _editing: root.mode === "edit"
    readonly property var _state: root.rateCard ? (root.rateCard.state || {}) : ({})
    width: 560
    title: root._editing ? "Edit Rate Card" : "Create Rate Card"
    subtitle: root._editing
        ? "Rename this active Rate Card without changing historical rates."
        : "Create a project Rate Card for authoritative cost or billing rates."
    primaryText: root._editing ? "Save Changes" : "Create Rate Card"
    primaryIcon: root._editing ? "save" : "add"
    primaryEnabled: !root.busy && root.projectId.length > 0

    function submitDialog() {
        const name = nameField.text.trim()
        if (!name) {
            root.errorMessage = "Rate Card name is required."
            nameField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted({
            "projectId": root.projectId,
            "scope": "project",
            "rateCardId": root.rateCard ? String(root.rateCard.id || "") : "",
            "version": Number(root._state.version || 0),
            "name": name
        })
    }
    onOpened: {
        nameField.text = root._editing && root.rateCard ? String(root.rateCard.title || "") : ""
        root.errorMessage = ""
        nameField.forceActiveFocus()
    }
    onRejected: root.close()

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Rate Card name"
        required: true
        AppControls.TextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "Project delivery rates"
            maximumLength: 160
        }
    }
}
