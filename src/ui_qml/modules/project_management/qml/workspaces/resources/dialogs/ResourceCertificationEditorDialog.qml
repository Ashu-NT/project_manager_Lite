import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Add Certification"
    property var certificationData: ({})

    signal submitted(var payload)

    title: root.modeTitle
    subtitle: root.modeTitle === "Add Certification"
        ? "Record a professional certification or compliance credential."
        : "Update this credential using its current version."
    primaryText: root.modeTitle === "Add Certification" ? "Add Certification" : "Save Changes"
    primaryIcon: root.modeTitle === "Add Certification" ? "add" : "save"
    width: 680

    onOpened:   root._reset()
    onAccepted: root._submit()
    onRejected: root.close()

    function _reset() {
        const state = root.certificationData || {}
        certCodeField.text = String(state.certificationCode || "")
        certNameField.text = String(state.certificationName || "")
        certificateNumberField.text = String(state.certificateNumber || "")
        issuedDateField.text = String(state.issuedDate || "")
        expiryDateField.text = String(state.expiryDate || "")
        issuerField.text = String(state.issuer || "")
        notesField.text = String(state.notes || "")
        root.errorMessage = ""
    }

    function _submit() {
        if (certCodeField.text.trim().length === 0) {
            root.errorMessage = "Certification code is required."
            return
        }
        root.errorMessage = ""
        root.submitted({
            "certId": String((root.certificationData || {}).id || ""),
            "expectedVersion": Number((root.certificationData || {}).version || 0),
            "certCode": certCodeField.text.trim(),
            "certName": certNameField.text.trim(),
            "issuedDate": issuedDateField.text.trim(),
            "expiryDate": expiryDateField.text.trim(),
            "certificateNumber": certificateNumberField.text.trim(),
            "issuer": issuerField.text.trim(),
            "notes": notesField.text.trim()
        })
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        id: certificationFormGrid
        Layout.fillWidth: true
        columns: root.width > 560 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Cert Code"
            required: true
            AppControls.TextField { id: certCodeField; Layout.fillWidth: true; placeholderText: "e.g. ISO-9001" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            required: true
            label: "Cert Name"
            AppControls.TextField { id: certNameField; Layout.fillWidth: true; placeholderText: "e.g. ISO 9001 Quality Management" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Certificate #"
            AppControls.TextField { id: certificateNumberField; Layout.fillWidth: true; placeholderText: "Credential number" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Issuer"
            AppControls.TextField { id: issuerField; Layout.fillWidth: true; placeholderText: "e.g. ISO" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Issued Date"
            AppControls.DateField { id: issuedDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD"; popupBoundaryItem: certificationFormGrid }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Expiry Date"
            AppControls.DateField { id: expiryDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD"; popupBoundaryItem: certificationFormGrid }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Notes"
            AppControls.TextField { id: notesField; Layout.fillWidth: true; placeholderText: "Optional notes" }
        }
    }
}
