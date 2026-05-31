import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var documentOptions: []

    signal submitted(string documentId)

    width: 500
    title: "Link Document"
    subtitle: "Link a shared document to this inventory item."
    errorMessage: root.validationMessage
    primaryText: "Link Document"
    primaryIcon: "add"
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property string currentDocumentId: String((documentOptions[documentCombo.currentIndex] || { "value": "" }).value || "")

    function submitDialog() {
        if (root.currentDocumentId.length === 0) {
            root.validationMessage = "Choose a document before saving."
            return
        }
        root.validationMessage = ""
        root.submitted(root.currentDocumentId)
    }

    onOpened: {
        documentCombo.currentIndex = 0
        root.validationMessage = ""
    }

    AppControls.ComboBox {
        id: documentCombo
        Layout.fillWidth: true
        model: root.documentOptions
        textRole: "label"
    }
}
