import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var typeOptions: []
    property var workspaceController: null
    property string partyCode: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    title: root.mode === "create" ? "New Party" : "Edit Party"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (root.partyCode.trim().length === 0) {
            root.errorMessage = "Party code is required."
            return
        }
        if (partyNameField.text.trim().length === 0) {
            root.errorMessage = "Party name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    readonly property var formData: ({
        partyId: root.draft.partyId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        partyCode: root.partyCode.trim(),
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
        root.partyCode = root.draft.partyCode || ""
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

    AppWidgets.CodeFieldRow {
        Layout.fillWidth: true
        label: "Party Code"
        value: root.partyCode
        placeholderText: "Auto-generated if empty"
        required: true
        generateVisible: true
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onValueEdited: function(code) { root.partyCode = code }
        onGenerateRequested: {
            if (root.workspaceController) {
                const suggested = root.workspaceController.generateEntityCode("party", root.formData)
                if (suggested && suggested.length > 0) {
                    root.partyCode = suggested
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Party Name"
        required: true

        AppControls.TextField {
            id: partyNameField
            Layout.fillWidth: true
            placeholderText: "e.g. Acme Industrial Supplies"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Party Type"

        AppControls.ComboBox {
            id: typeCombo
            Layout.fillWidth: true
            model: typeModel
            textRole: "label"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Legal Name"

            AppControls.TextField {
                id: legalNameField
                Layout.fillWidth: true
                placeholderText: "Registered legal entity name"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Contact Name"

            AppControls.TextField {
                id: contactNameField
                Layout.fillWidth: true
                placeholderText: "Primary contact"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Email"

            AppControls.TextField {
                id: emailField
                Layout.fillWidth: true
                placeholderText: "name@company.com"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Phone"

            AppControls.TextField {
                id: phoneField
                Layout.fillWidth: true
                placeholderText: "+1 555 0100"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Country"

            AppControls.TextField {
                id: countryField
                Layout.fillWidth: true
                placeholderText: "e.g. Netherlands"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "City"

            AppControls.TextField {
                id: cityField
                Layout.fillWidth: true
                placeholderText: "e.g. Rotterdam"
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Address Line 1"

        AppControls.TextField {
            id: addressLine1Field
            Layout.fillWidth: true
            placeholderText: "Street and number"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Address Line 2"

        AppControls.TextField {
            id: addressLine2Field
            Layout.fillWidth: true
            placeholderText: "Suite, unit, or building (optional)"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Postal Code"

            AppControls.TextField {
                id: postalCodeField
                Layout.fillWidth: true
                placeholderText: "e.g. 3011 AA"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Website"

            AppControls.TextField {
                id: websiteField
                Layout.fillWidth: true
                placeholderText: "https://example.com"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Tax Registration"

            AppControls.TextField {
                id: taxRegistrationField
                Layout.fillWidth: true
                placeholderText: "VAT / tax number"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "External Reference"

            AppControls.TextField {
                id: externalReferenceField
                Layout.fillWidth: true
                placeholderText: "ERP or vendor reference"
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"

        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            placeholderText: "Relationship notes or context"
            wrapMode: TextEdit.WordWrap
        }
    }

    AppControls.CheckBox {
        id: activeCheck

        text: "Active party"
    }
}
