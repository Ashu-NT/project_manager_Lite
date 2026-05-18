import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var documentOptions: []
    property string validationMessage: ""

    signal submitted(string documentId)

    modal: true
    width: 500
    title: "Link Document"
    closePolicy: Popup.CloseOnEscape

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

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Select a shared document to attach to the selected inventory item."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
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

        ComboBox {
            id: documentCombo
            Layout.fillWidth: true
            model: root.documentOptions
            textRole: "label"
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        Button {
            text: "Link"
            enabled: root.documentOptions.length > 0
            onClicked: root.submitDialog()
        }
    }
}
