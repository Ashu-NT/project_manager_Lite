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
    property var roleOptions: []
    property var workspaceController: null
    property string partyCode: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthWide
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
        partyType: _currentValue(typeModel, typeCombo) || "ORGANIZATION",
        roles: _selectedRoles(),
        legalName: legalNameField.text.trim(),
        registrationNumber: registrationNumberField.text.trim(),
        taxIdentifier: taxIdentifierField.text.trim(),
        externalReference: externalReferenceField.text.trim(),
        contactName: contactNameField.text.trim(),
        email: emailField.text.trim(),
        phone: phoneField.text.trim(),
        website: websiteField.text.trim(),
        country: countryField.text.trim(),
        city: cityField.text.trim(),
        addressLine1: addressLine1Field.text.trim(),
        addressLine2: addressLine2Field.text.trim(),
        postalCode: postalCodeField.text.trim(),
        notes: notesField.text.trim()
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
        root.roleOptions = options.roleOptions || []
        _reloadOptionModel(typeModel, root.typeOptions)
        _reloadRoleModel()
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

    function _reloadRoleModel() {
        roleModel.clear()
        const selected = root.draft.roles || []
        for (let index = 0; index < root.roleOptions.length; index += 1) {
            const option = root.roleOptions[index]
            roleModel.append({
                label: option.label || "",
                value: option.value || "",
                selected: selected.indexOf(option.value) !== -1
            })
        }
    }

    function _selectedRoles() {
        const values = []
        for (let index = 0; index < roleModel.count; index += 1) {
            const option = roleModel.get(index)
            if (option.selected) {
                values.push(option.value)
            }
        }
        return values
    }

    function _loadDraft() {
        root.partyCode = root.draft.partyCode || ""
        partyNameField.text = root.draft.partyName || ""
        legalNameField.text = root.draft.legalName || ""
        registrationNumberField.text = root.draft.registrationNumber || ""
        taxIdentifierField.text = root.draft.taxIdentifier || ""
        externalReferenceField.text = root.draft.externalReference || ""
        contactNameField.text = root.draft.contactName || ""
        emailField.text = root.draft.email || ""
        phoneField.text = root.draft.phone || ""
        websiteField.text = root.draft.website || ""
        countryField.text = root.draft.country || ""
        cityField.text = root.draft.city || ""
        addressLine1Field.text = root.draft.addressLine1 || ""
        addressLine2Field.text = root.draft.addressLine2 || ""
        postalCodeField.text = root.draft.postalCode || ""
        notesField.text = root.draft.notes || ""
        _setCurrentIndex(typeModel, typeCombo, root.draft.partyType || "ORGANIZATION")
        _reloadRoleModel()
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
    ListModel { id: roleModel }

    GridLayout {
        id: formGrid
        Layout.fillWidth: true
        columns: formGrid.width >= 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        // ── IDENTITY ─────────────────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Identity"
        }

        AppWidgets.CodeFieldRow {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
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
            required: true
            helperText: "What this party is -- Organization or Individual."

            AppControls.ComboBox {
                id: typeCombo
                Layout.fillWidth: true
                model: typeModel
                textRole: "label"
            }
        }

        // ── BUSINESS ROLES ───────────────────────────────────────────────
        // A wrapping chip/toggle layout, not a tall vertical checkbox list --
        // still a real multi-select (ChoiceChip is a styled QQC2.CheckBox,
        // so keyboard focus/Space-Enter toggle/accessible checked state all
        // come for free). Party Type (what the party IS) stays directly
        // above; roles (what the party DOES) are a separate, independent,
        // multi-valued concept -- never merged into Party Type.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            spacing: Theme.AppTheme.spacingSm

            AppWidgets.SectionHeading {
                Layout.fillWidth: true
                label: "Business Roles"
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Select all roles that apply."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: roleModel

                    delegate: AppControls.ChoiceChip {
                        required property int index
                        required property string label
                        required property bool selected

                        text: label
                        checked: selected
                        onToggled: roleModel.setProperty(index, "selected", checked)
                    }
                }
            }
        }

        // ── LEGAL & REGISTRATION ─────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Legal & Registration"
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Legal Name"
            helperText: "Full registered legal entity name, if different from the party name."

            AppControls.TextField {
                id: legalNameField
                Layout.fillWidth: true
                placeholderText: "Registered legal entity name"
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

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Registration Number"
            helperText: "Company registration number."

            AppControls.TextField {
                id: registrationNumberField
                Layout.fillWidth: true
                placeholderText: "e.g. company registration number"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Tax Identifier"
            helperText: "VAT / tax identification number."

            AppControls.TextField {
                id: taxIdentifierField
                Layout.fillWidth: true
                placeholderText: "e.g. VAT / tax number"
            }
        }

        // ── CONTACT INFORMATION ──────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Contact Information"
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

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Website"

            AppControls.TextField {
                id: websiteField
                Layout.fillWidth: true
                placeholderText: "https://example.com"
            }
        }

        // ── ADDRESS ──────────────────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Address"
        }

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

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Postal Code"

            AppControls.TextField {
                id: postalCodeField
                Layout.fillWidth: true
                placeholderText: "e.g. 3011 AA"
            }
        }

        // ── NOTES ────────────────────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Notes"
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Notes"

            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 96
                placeholderText: "Relationship notes or context"
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}
