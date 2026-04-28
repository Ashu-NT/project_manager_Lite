import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "approve"
    property string requestId: ""
    property string requestTitle: ""

    signal decisionConfirmed(string mode, string requestId, string note)

    modal: true
    focus: true
    width: 520
    closePolicy: Popup.NoAutoClose
    title: root.mode === "reject" ? "Reject Request" : "Approve Request"

    function openForDecision(modeValue, itemData) {
        root.mode = modeValue || "approve"
        root.requestId = itemData && itemData.id ? String(itemData.id) : ""
        root.requestTitle = itemData && itemData.title ? String(itemData.title) : ""
        noteField.text = ""
        open()
        noteField.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.requestTitle.length > 0
                ? root.requestTitle
                : "Add an optional note for this decision."
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            text: root.mode === "reject"
                ? "Capture an optional rejection reason before closing the request."
                : "Capture an optional approval note before applying the request."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        TextArea {
            id: noteField

            Layout.fillWidth: true
            Layout.preferredHeight: 140
            placeholderText: root.mode === "reject"
                ? "Optional rejection reason"
                : "Optional approval note"
            wrapMode: TextEdit.Wrap
            selectByMouse: true
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
                text: root.mode === "reject" ? "Reject" : "Approve"
                danger: root.mode === "reject"
                enabled: root.requestId.length > 0
                onClicked: root.decisionConfirmed(root.mode, root.requestId, noteField.text)
            }
        }
    }
}
