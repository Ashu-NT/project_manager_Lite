import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var typeOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New Party" : "Edit Party"

    readonly property var formData: ({
        partyId: root.draft.partyId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        partyCode: partyCodeField.text.trim(),
        partyName: partyNameField.text.trim(),
        partyType: _currentValue(typeModel, typeCombo) || "GENERAL",
        legalName: legalNameField.text.trim(),
        contactName: contactNameField.text.trim(),
        email: emailField.text.trim(),
        phone: phoneField.text.trim(),
        country: countryField.text.trim(),
        city: cityField.text.trim(),
        addressLine1: addressLine1Field.text.trim(),
        addressLine2: addressLine2Field.text.trim(),
        postalCode: postalCodeField.text.trim(),
        website: websiteField.text.trim(),
        taxRegistrationNumber: taxRegistrationField.text.trim(),
        externalReference: externalReferenceField.text.trim(),
        notes: notesField.text.trim(),
        isActive: activeCheck.checked
    })

    function openForCreate(options) {
        root.mode = "create"
        root.draft = ({})
        _assignOptions(options || ({}))
        _loadDraft()
        open()
    }

    function openForEdit(draftData, options) {
        root.mode = "edit"
        root.draft = draftData || ({})
        _assignOptions(options || ({}))
        _loadDraft()
        open()
    }

    function _assignOptions(options) {
        root.typeOptions = options.typeOptions || []
        _reloadOptionModel(typeModel, root.typeOptions)
    }

    function _reloadOptionModel(model, options) {
        model.clear()
        for (let index = 0; index < options.length; index += 1) {
            const option = options[index]
            model.append({
                label: option.label || "",
                value: option.value || ""
            })
        }
    }

    function _loadDraft() {
        partyCodeField.text = root.draft.partyCode || ""
        partyNameField.text = root.draft.partyName || ""
        legalNameField.text = root.draft.legalName || ""
        contactNameField.text = root.draft.contactName || ""
        emailField.text = root.draft.email || ""
        phoneField.text = root.draft.phone || ""
        countryField.text = root.draft.country || ""
        cityField.text = root.draft.city || ""
        addressLine1Field.text = root.draft.addressLine1 || ""
        addressLine2Field.text = root.draft.addressLine2 || ""
        postalCodeField.text = root.draft.postalCode || ""
        websiteField.text = root.draft.website || ""
        taxRegistrationField.text = root.draft.taxRegistrationNumber || ""
        externalReferenceField.text = root.draft.externalReference || ""
        notesField.text = root.draft.notes || ""
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _setCurrentIndex(typeModel, typeCombo, root.draft.partyType || "GENERAL")
    }

    function _setCurrentIndex(model, combo, value) {
        for (let index = 0; index < model.count; index += 1) {
            if (model.get(index).value === value) {
                combo.currentIndex = index
                return
            }
        }
        combo.currentIndex = 0
    }

    function _currentValue(model, combo) {
        if (combo.currentIndex < 0 || combo.currentIndex >= model.count) {
            return ""
        }
        return model.get(combo.currentIndex).value || ""
    }

    ListModel { id: typeModel }

    contentItem: ScrollView {
        implicitWidth: 580
        implicitHeight: 520
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: partyCodeField

                    Layout.preferredWidth: 180
                    placeholderText: "Party code"
                }

                TextField {
                    id: partyNameField

                    Layout.fillWidth: true
                    placeholderText: "Party name"
                }
            }

            ComboBox {
                id: typeCombo

                Layout.fillWidth: true
                model: typeModel
                textRole: "label"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: legalNameField

                    Layout.fillWidth: true
                    placeholderText: "Legal name"
                }

                TextField {
                    id: contactNameField

                    Layout.fillWidth: true
                    placeholderText: "Contact name"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: emailField

                    Layout.fillWidth: true
                    placeholderText: "Email"
                }

                TextField {
                    id: phoneField

                    Layout.fillWidth: true
                    placeholderText: "Phone"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: countryField

                    Layout.fillWidth: true
                    placeholderText: "Country"
                }

                TextField {
                    id: cityField

                    Layout.fillWidth: true
                    placeholderText: "City"
                }
            }

            TextField {
                id: addressLine1Field

                Layout.fillWidth: true
                placeholderText: "Address line 1"
            }

            TextField {
                id: addressLine2Field

                Layout.fillWidth: true
                placeholderText: "Address line 2"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: postalCodeField

                    Layout.fillWidth: true
                    placeholderText: "Postal code"
                }

                TextField {
                    id: websiteField

                    Layout.fillWidth: true
                    placeholderText: "Website"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: taxRegistrationField

                    Layout.fillWidth: true
                    placeholderText: "Tax registration"
                }

                TextField {
                    id: externalReferenceField

                    Layout.fillWidth: true
                    placeholderText: "External reference"
                }
            }

            TextArea {
                id: notesField

                Layout.fillWidth: true
                Layout.preferredHeight: 96
                placeholderText: "Notes"
                wrapMode: TextEdit.WordWrap
            }

            CheckBox {
                id: activeCheck

                text: "Active party"
            }
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
                enabled: partyCodeField.text.trim().length > 0
                    && partyNameField.text.trim().length > 0
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
