import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string documentId: ""

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 520
    closePolicy: Popup.NoAutoClose
    title: "Add Document Link"

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

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Connect the selected shared document to a business record in another module."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        TextField {
            id: moduleCodeField

            Layout.fillWidth: true
            placeholderText: "Module code"
        }

        TextField {
            id: entityTypeField

            Layout.fillWidth: true
            placeholderText: "Entity type"
        }

        TextField {
            id: entityIdField

            Layout.fillWidth: true
            placeholderText: "Entity id"
        }

        TextField {
            id: linkRoleField

            Layout.fillWidth: true
            placeholderText: "Link role"
        }
    }

    footer: Frame {
        padding: Theme.AppTheme.marginMd

        RowLayout {
            anchors.fill: parent
            spacing: Theme.AppTheme.spacingSm

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "Cancel"
                onClicked: root.close()
            }

            AppControls.PrimaryButton {
                enabled: root.documentId.length > 0
                    && moduleCodeField.text.trim().length > 0
                    && entityTypeField.text.trim().length > 0
                    && entityIdField.text.trim().length > 0
                text: "Add Link"
                onClicked: root.saveRequested(root.formData)
            }
        }
    }
}
