import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string documentId: ""

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 520
    title: "Add Document Link"
    subtitle: "Connect the selected shared document to a business record in another module."
    primaryText: "Add Link"
    primaryIcon: "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (moduleCodeField.text.trim().length === 0) {
            root.errorMessage = "Module code is required."
            return
        }
        if (entityTypeField.text.trim().length === 0) {
            root.errorMessage = "Entity type is required."
            return
        }
        if (entityIdField.text.trim().length === 0) {
            root.errorMessage = "Entity id is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.formData)
    }

    readonly property var formData: ({
        documentId: root.documentId,
        moduleCode: moduleCodeField.text.trim(),
        entityType: entityTypeField.text.trim(),
        entityId: entityIdField.text.trim(),
        linkRole: linkRoleField.text.trim()
    })

    function openForCreate(targetDocumentId) {
        root.documentId = targetDocumentId || ""
        moduleCodeField.text = ""
        entityTypeField.text = ""
        entityIdField.text = ""
        linkRoleField.text = ""
        open()
    }

    AppControls.TextField {
        id: moduleCodeField

        Layout.fillWidth: true
        placeholderText: "Module code"
    }

    AppControls.TextField {
        id: entityTypeField

        Layout.fillWidth: true
        placeholderText: "Entity type"
    }

    AppControls.TextField {
        id: entityIdField

        Layout.fillWidth: true
        placeholderText: "Entity id"
    }

    AppControls.TextField {
        id: linkRoleField

        Layout.fillWidth: true
        placeholderText: "Link role"
    }
}
