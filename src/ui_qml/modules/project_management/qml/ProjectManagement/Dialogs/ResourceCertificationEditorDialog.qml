import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 480
    height: Math.min(560, parent ? parent.height - Theme.AppTheme.marginLg * 2 : 560)
    title: "Add Certification"
    closePolicy: Popup.CloseOnEscape

    function _reset() {
        certCodeField.text = ""
        certNameField.text = ""
        issuedDateField.text = ""
        expiryDateField.text = ""
        issuingBodyField.text = ""
        notesField.text = ""
        root.validationMessage = ""
    }

    function _submit() {
        if (certCodeField.text.trim().length === 0) {
            root.validationMessage = "Certification code is required."
            return
        }
        root.validationMessage = ""
        root.submitted({
            "certCode": certCodeField.text.trim(),
            "certName": certNameField.text.trim(),
            "issuedDate": issuedDateField.text.trim(),
            "expiryDate": expiryDateField.text.trim(),
            "issuingBody": issuingBodyField.text.trim(),
            "notes": notesField.text.trim()
        })
    }

    onOpened: root._reset()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: Flickable {
        contentWidth: width
        contentHeight: _formCol.implicitHeight
        clip: true

        ColumnLayout {
            id: _formCol
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                Layout.fillWidth: true
                text: "Record a professional certification or compliance credential for this resource."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                AppControls.Label { text: "Cert Code *"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField {
                    id: certCodeField
                    Layout.fillWidth: true
                    placeholderText: "e.g. ISO-9001"
                }

                AppControls.Label { text: "Cert Name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField {
                    id: certNameField
                    Layout.fillWidth: true
                    placeholderText: "e.g. ISO 9001 Quality Management"
                }

                AppControls.Label { text: "Issuing Body"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField {
                    id: issuingBodyField
                    Layout.fillWidth: true
                    placeholderText: "e.g. ISO"
                }

                AppControls.Label { text: "Issued Date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.DateField {
                    id: issuedDateField
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }

                AppControls.Label { text: "Expiry Date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.DateField {
                    id: expiryDateField
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }

                AppControls.Label { text: "Notes"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                AppControls.TextField {
                    id: notesField
                    Layout.fillWidth: true
                    placeholderText: "Optional notes"
                }
            }
        }
    }

    footer: AppControls.DialogActionFooter {
        Item { Layout.fillWidth: true }
        AppControls.SecondaryButton {
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }
        AppControls.PrimaryButton {
            text: "Add Certification"
            iconName: "add"
            onClicked: root._submit()
        }
    }
}
