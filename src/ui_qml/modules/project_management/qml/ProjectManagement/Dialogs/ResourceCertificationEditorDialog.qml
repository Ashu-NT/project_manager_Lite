import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    signal submitted(var payload)

    title:        "Add Certification"
    subtitle:     "Record a professional certification or compliance credential for this resource."
    primaryText:  "Add Certification"
    primaryIcon:  "add"
    width: 480

    onOpened:   root._reset()
    onAccepted: root._submit()
    onRejected: root.close()

    function _reset() {
        certCodeField.text = ""
        certNameField.text = ""
        issuedDateField.text = ""
        expiryDateField.text = ""
        issuingBodyField.text = ""
        notesField.text = ""
        root.errorMessage = ""
    }

    function _submit() {
        if (certCodeField.text.trim().length === 0) {
            root.errorMessage = "Certification code is required."
            return
        }
        root.errorMessage = ""
        root.submitted({
            "certCode": certCodeField.text.trim(),
            "certName": certNameField.text.trim(),
            "issuedDate": issuedDateField.text.trim(),
            "expiryDate": expiryDateField.text.trim(),
            "issuingBody": issuingBodyField.text.trim(),
            "notes": notesField.text.trim()
        })
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Cert Code *"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: certCodeField; Layout.fillWidth: true; placeholderText: "e.g. ISO-9001" }

        AppControls.Label { text: "Cert Name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: certNameField; Layout.fillWidth: true; placeholderText: "e.g. ISO 9001 Quality Management" }

        AppControls.Label { text: "Issuing Body"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: issuingBodyField; Layout.fillWidth: true; placeholderText: "e.g. ISO" }

        AppControls.Label { text: "Issued Date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.DateField { id: issuedDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

        AppControls.Label { text: "Expiry Date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.DateField { id: expiryDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

        AppControls.Label { text: "Notes"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: notesField; Layout.fillWidth: true; placeholderText: "Optional notes" }
    }
}
