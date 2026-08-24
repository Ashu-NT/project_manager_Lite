import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string actionMode: "approve"
    property var reviewData: ({})

    signal submitted(var payload)

    width: Math.min(560, parent ? parent.width - Theme.AppTheme.spacingLg * 2 : 560)
    title: {
        if (root.actionMode === "reject") return "Return Timesheet"
        if (root.actionMode === "lock") return "Lock Timesheet Period"
        if (root.actionMode === "unlock") return "Unlock Timesheet Period"
        return "Approve Timesheet"
    }
    subtitle: String(root.reviewData.title || "Selected timesheet period")
    infoMessage: {
        const state = root.reviewData.state || {}
        const hours = String(state.totalHoursLabel || "")
        const status = String(root.reviewData.statusLabel || state.status || "")
        return [hours, status].filter(function(value) { return value.length > 0 }).join(" | ")
    }
    primaryText: root.actionMode === "approve"
        ? "Approve"
        : (root.actionMode === "lock" ? "Lock Period" : "Unlock Period")
    primaryIcon: root.actionMode === "approve" ? "approve" : (root.actionMode === "lock" ? "lock" : "edit")
    showPrimary: root.actionMode !== "reject"
    destructiveText: "Return Timesheet"
    destructiveIcon: "close"
    showDestructive: root.actionMode === "reject"
    destructiveEnabled: String(noteArea.text || "").trim().length > 0

    function submitDialog() {
        const state = root.reviewData.state || {}
        const periodId = String(state.periodId || root.reviewData.id || "")
        const expectedVersion = Number(state.version || 0)
        const note = String(noteArea.text || "").trim()
        if (!periodId || expectedVersion < 1) {
            root.errorMessage = "Refresh this review item before making a decision."
            return
        }
        if (root.actionMode === "reject" && !note) {
            root.errorMessage = "A return reason is required."
            return
        }
        root.errorMessage = ""
        root.submitted({
            "periodId": periodId,
            "expectedVersion": expectedVersion,
            "note": note
        })
    }

    onOpened: {
        noteArea.text = ""
        root.errorMessage = ""
    }
    onAccepted: root.submitDialog()
    onDestructiveRequested: root.submitDialog()
    onRejected: root.close()

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: root.actionMode === "reject" ? "Return reason" : "Decision note"
        required: root.actionMode === "reject"

        AppControls.TextArea {
            id: noteArea
            Layout.fillWidth: true
            Layout.preferredHeight: 112
            placeholderText: root.actionMode === "reject"
                ? "Explain what must be corrected before resubmission."
                : "Add an optional reviewer note."
            wrapMode: TextEdit.WordWrap
        }
    }
}
