import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Governed decision dialog for the canonical ProjectCostEntry lifecycle.
// One dialog, three modes, so a reason/date field is defined once instead
// of duplicated across separate reject/post/reverse dialog components.
//   mode: "reject"  -> optional notes; returned to draft.
//   mode: "post"    -> required posting date; approved -> posted.
//   mode: "reverse" -> required posting date + required reason; posted ->
//                      reversed, with a new signed reversal entry created.
// Only the fields the backend actually requires for that mode are shown.
AppWidgets.EntityDialog {
    id: root

    property string mode: "reject"
    property string entryId: ""
    property int rowVersion: 0
    property string commandId: ""

    signal decided(string mode, var payload)

    readonly property bool _isReject: root.mode === "reject"
    readonly property bool _isPost: root.mode === "post"
    readonly property bool _isReverse: root.mode === "reverse"
    readonly property bool _reasonRequired: root._isReverse

    modal: true
    width: 480
    closePolicy: Popup.CloseOnEscape
    title: root._isReject ? "Reject Actual" : (root._isPost ? "Post Actual" : "Reverse Actual")
    subtitle: root._isReject
        ? "Return this actual to draft. It can be corrected and resubmitted."
        : (root._isPost
            ? "Post this approved actual into the ledger for the posting date below."
            : "Create a signed reversal of this posted actual. The original entry becomes immutable once reversed.")
    primaryText: root._isReject ? "Reject" : (root._isPost ? "Post" : "Reverse")
    primaryIcon: root._isReject ? "reject" : (root._isPost ? "save" : "delete")

    onAccepted: root.submitDialog()
    onRejected: root.close()

    function populateDefaults() {
        notesField.text = ""
        postingDateField.text = Qt.formatDate(new Date(), "yyyy-MM-dd")
        root.errorMessage = ""
    }

    function buildPayload() {
        const payload = {
            "entryId": root.entryId,
            "rowVersion": root.rowVersion
        }
        if (root._isReject) {
            payload["notes"] = notesField.text
        } else if (root._isPost) {
            payload["postingDate"] = postingDateField.text
        } else if (root._isReverse) {
            payload["postingDate"] = postingDateField.text
            payload["reason"] = notesField.text
            payload["commandId"] = root.commandId
        }
        return payload
    }

    function submitDialog() {
        if ((root._isPost || root._isReverse) && postingDateField.text.trim().length === 0) {
            root.errorMessage = "Posting date is required."
            return
        }
        if (root._reasonRequired && notesField.text.trim().length === 0) {
            root.errorMessage = "A reversal reason is required."
            return
        }
        root.errorMessage = ""
        root.decided(root.mode, root.buildPayload())
    }

    onOpened: root.populateDefaults()

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root._isPost || root._isReverse
            label: "Posting date"
            required: true
            AppControls.DateField {
                id: postingDateField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root._isReject || root._isReverse
            label: root._isReverse ? "Reversal reason" : "Rejection notes (optional)"
            required: root._reasonRequired
            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                wrapMode: TextEdit.WordWrap
                placeholderText: root._isReverse
                    ? "Explain why this posted actual must be reversed."
                    : "Optional context for the submitter."
            }
        }
    }
}
