import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var commentData: ({})

    signal submitted(var payload)

    width: 560
    title: "Delete Comment"
    subtitle: "Remove this comment from the discussion while retaining its moderation record."
    infoMessage: "The original comment remains preserved for authorized audit and investigation workflows."
    showPrimary: false
    showDestructive: true
    destructiveText: "Delete Comment"
    destructiveIcon: "delete"
    closePolicy: Popup.CloseOnEscape

    function selectedState() {
        return root.commentData && root.commentData.state
            ? root.commentData.state
            : (root.commentData || {})
    }

    function submitDialog() {
        const state = root.selectedState()
        const commentId = String(state.commentId || root.commentData.id || "")
        const revision = Number(state.revision || 0)
        if (!commentId || revision < 1) {
            root.errorMessage = "The comment changed or could not be identified. Refresh the discussion and try again."
            return
        }
        root.errorMessage = ""
        root.submitted({
            "commentId": commentId,
            "expectedRevision": revision,
            "reason": String(reasonArea.text || "").trim()
        })
    }

    onOpened: {
        reasonArea.text = ""
        root.errorMessage = ""
    }
    onDestructiveRequested: root.submitDialog()
    onRejected: root.close()

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Removal reason (optional)"

        AppControls.TextArea {
            id: reasonArea
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            placeholderText: "For example: duplicate, sensitive information, or policy violation."
            wrapMode: TextEdit.WordWrap
        }
    }
}
