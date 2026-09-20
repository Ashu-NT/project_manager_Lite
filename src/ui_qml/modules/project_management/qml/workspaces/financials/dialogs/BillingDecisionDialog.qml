pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "billingDecisionDialog"
    property string action: ""
    property var preparation: ({})
    property string lineId: ""
    readonly property var state: root.preparation.state || ({})
    readonly property var capabilities: ({
        "submit": "canSubmit", "cancel": "canCancel", "remove": "canRemoveSource",
        "approve": "canApprove", "reject": "canReject", "request_delivery": "canRequestDelivery"
    })
    signal submitted(string action, var preparation, string lineId, string note)
    title: root.action === "approve" ? "Approve Billing Preparation"
        : root.action === "reject" ? "Reject Billing Preparation"
        : root.action === "cancel" ? "Cancel Billing Draft"
        : root.action === "remove" ? "Remove Billing Source"
        : root.action === "request_delivery" ? "Request Accounting Handoff"
        : "Submit Billing Preparation"
    subtitle: "Confirm the PM commercial action for " + String(root.preparation.title || "this preparation")
        + ". This does not create an invoice or receivable."
    primaryText: "Confirm"
    primaryIcon: root.action === "reject" || root.action === "cancel" ? "reject" : "approve"
    primaryEnabled: !root.busy && Boolean(root.state[root.capabilities[root.action]])
        && (root.action !== "remove" || root.lineId.length > 0)
    initialFocusTarget: notes
    onOpened: { notes.text = ""; root.errorMessage = "" }
    function submitDialog() {
        if (!root.primaryEnabled) return
        if (root.action === "reject" && !notes.text.trim()) {
            root.errorMessage = "A rejection reason is required."
            notes.forceActiveFocus()
            return
        }
        root.submitted(root.action, root.preparation, root.lineId, notes.text.trim())
    }
    AppWidgets.FormField {
        Layout.fillWidth: true
        label: root.action === "reject" ? "Rejection reason" : "Decision notes"
        required: root.action === "reject"
        visible: root.action === "approve" || root.action === "reject"
        AppControls.TextArea {
            id: notes
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            wrapMode: TextEdit.WordWrap
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                    const forward = event.key === Qt.Key_Tab && !(event.modifiers & Qt.ShiftModifier)
                    notes.nextItemInFocusChain(forward).forceActiveFocus(Qt.TabFocusReason)
                    event.accepted = true
                }
            }
        }
    }
}
