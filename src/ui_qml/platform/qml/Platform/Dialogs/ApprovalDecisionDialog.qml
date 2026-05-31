import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "approve"
    property string requestId: ""
    property string requestTitle: ""

    signal decisionConfirmed(string mode, string requestId, string note)

    modal: true
    focus: true
    width: 520
    title: root.mode === "reject" ? "Reject Request" : "Approve Request"
    subtitle: root.requestTitle.length > 0
        ? root.requestTitle
        : (root.mode === "reject"
            ? "Capture an optional rejection reason before closing the request."
            : "Capture an optional approval note before applying the request.")
    primaryText: root.mode === "reject" ? "Reject" : "Approve"
    primaryIcon: root.mode === "reject" ? "reject" : "approve"
    onAccepted: root.decisionConfirmed(root.mode, root.requestId, noteField.text)
    onRejected: root.close()

    function openForDecision(modeValue, itemData) {
        root.mode = modeValue || "approve"
        root.requestId = itemData && itemData.id ? String(itemData.id) : ""
        root.requestTitle = itemData && itemData.title ? String(itemData.title) : ""
        noteField.text = ""
        open()
        noteField.forceActiveFocus()
    }

    AppControls.TextArea {
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
