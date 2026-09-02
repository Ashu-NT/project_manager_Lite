import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string action: "submit"
    property var budget: null
    property var line: null
    signal decided(
        string action, string budgetId, int budgetVersion,
        string approvalRequestId, string lineId, int lineVersion, string notes
    )

    readonly property var _budgetState: root.budget ? (root.budget.state || {}) : ({})
    readonly property var _lineState: root.line ? (root.line.state || {}) : ({})
    readonly property bool _isDelete: root.action === "delete_budget" || root.action === "delete_line"

    width: 520
    title: root.action === "submit" ? "Submit Budget"
        : root.action === "request_approval" ? "Request Budget Approval"
        : root.action === "approve" ? "Approve Budget Request"
        : root.action === "reject" ? "Reject Budget Request"
        : root.action === "close" ? "Close Approved Budget"
        : root.action === "delete_line" ? "Delete Budget Line"
        : "Delete Draft Budget"
    subtitle: root.action === "submit"
        ? "Submission freezes this revision and its lines for review."
        : root.action === "request_approval"
            ? "Create a Platform Approval request. A different authorized principal must decide it."
        : root.action === "approve" || root.action === "reject"
            ? "This decision is executed by the shared Platform Approval authority."
        : root.action === "close"
            ? "Closing is terminal and removes this revision from the current approved projection."
        : "This operation cannot be undone."
    primaryText: root.action === "request_approval" ? "Request Approval"
        : root.action === "delete_line" ? "Delete Line"
        : root.action === "delete_budget" ? "Delete Draft"
        : root.action.charAt(0).toUpperCase() + root.action.slice(1)
    primaryIcon: root._isDelete ? "delete"
        : root.action === "reject" ? "reject" : "approve"

    function submitDialog() {
        if (root.action === "reject" && !notesField.text.trim()) {
            root.errorMessage = "A rejection reason is required."
            notesField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.decided(
            root.action,
            String(root.budget ? root.budget.id || "" : ""),
            Number(root._budgetState.rowVersion || 0),
            String(root._budgetState.approvalRequestId || ""),
            String(root.line ? root.line.id || "" : ""),
            Number(root._lineState.rowVersion || 0),
            notesField.text.trim()
        )
    }

    onOpened: {
        notesField.text = ""
        root.errorMessage = ""
        notesField.forceActiveFocus()
    }
    onRejected: root.close()

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: !root._isDelete
        label: root.action === "reject" ? "Decision reason" : "Notes"
        required: root.action === "reject"
        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            wrapMode: TextEdit.WordWrap
            placeholderText: root.action === "reject"
                ? "Explain what must change before resubmission."
                : "Optional context for the audit trail"
        }
    }
}
