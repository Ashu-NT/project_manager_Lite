pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var moduleOptions: []
    property var countryOptions: []
    property var timezoneOptions: []
    property var currencyOptions: []
    property var workspaceController: null
    property string organizationCode: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthWide
    title: root.mode === "create" ? "New Organization" : "Edit Organization"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (root.organizationCode.trim().length === 0) {
            root.errorMessage = "Organization code is required."
            return
        }
        if (displayNameField.text.trim().length === 0) {
            root.errorMessage = "Display name is required."
            return
        }
        if (emailField.text.trim().length > 0 && !_isValidEmail(emailField.text.trim())) {
            root.errorMessage = "Enter a valid email address."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    function _isValidEmail(value) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
    }

    readonly property var formData: ({
        organizationId: root.draft.organizationId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        organizationCode: root.organizationCode.trim(),
        displayName: displayNameField.text.trim(),
        timezoneName: _currentValue(timezoneModel, timezoneCombo),
        baseCurrency: _currentValue(currencyModel, currencyCombo).toUpperCase(),
        initialModuleCodes: _selectedModuleCodes(),
        legalName: legalNameField.text.trim(),
        registrationNumber: registrationNumberField.text.trim(),
        taxId: taxIdField.text.trim(),
        addressLine1: addressLine1Field.text.trim(),
        addressLine2: addressLine2Field.text.trim(),
        postalCode: postalCodeField.text.trim(),
        city: cityField.text.trim(),
        stateRegion: stateRegionField.text.trim(),
        countryCode: _currentValue(countryModel, countryCombo),
        email: emailField.text.trim(),
        phone: phoneField.text.trim(),
        website: websiteField.text.trim()
    })

    function openForCreate(options) {
        root.mode = "create"
        root.draft = ({})
        root.moduleOptions = (options && options.moduleOptions) || []
        root.countryOptions = (options && options.countryOptions) || []
        root.timezoneOptions = (options && options.timezoneOptions) || []
        root.currencyOptions = (options && options.currencyOptions) || []
        _loadDraft()
        open()
    }

    function openForEdit(draftData, options) {
        root.mode = "edit"
        root.draft = draftData || ({})
        if (options) {
            root.moduleOptions = options.moduleOptions || []
            root.countryOptions = options.countryOptions || []
            root.timezoneOptions = options.timezoneOptions || []
            root.currencyOptions = options.currencyOptions || []
        }
        _loadDraft()
        open()
    }

    function _loadDraft() {
        root.organizationCode = root.draft.organizationCode || ""
        displayNameField.text = root.draft.displayName || ""
        legalNameField.text = root.draft.legalName || ""
        registrationNumberField.text = root.draft.registrationNumber || ""
        taxIdField.text = root.draft.taxId || ""
        addressLine1Field.text = root.draft.addressLine1 || ""
        addressLine2Field.text = root.draft.addressLine2 || ""
        postalCodeField.text = root.draft.postalCode || ""
        cityField.text = root.draft.city || ""
        stateRegionField.text = root.draft.stateRegion || ""
        emailField.text = root.draft.email || ""
        phoneField.text = root.draft.phone || ""
        websiteField.text = root.draft.website || ""
        _reloadModules()
        _reloadOptionModel(countryModel, root.countryOptions)
        _setCurrentIndex(countryModel, countryCombo, root.draft.countryCode || "")
        _reloadOptionModel(timezoneModel, root.timezoneOptions)
        _setCurrentIndex(timezoneModel, timezoneCombo, root.draft.timezoneName || "UTC")
        _reloadOptionModel(currencyModel, root.currencyOptions)
        _setCurrentIndex(currencyModel, currencyCombo, (root.draft.baseCurrency || "USD").toUpperCase())
    }

    function _reloadModules() {
        moduleModel.clear()
        const selected = root.draft.initialModuleCodes || []
        for (let index = 0; index < root.moduleOptions.length; index += 1) {
            const option = root.moduleOptions[index]
            moduleModel.append({
                label: option.label || "",
                value: option.value || "",
                supportingText: option.supportingText || "",
                selected: selected.indexOf(option.value) !== -1
            })
        }
    }

    function _selectedModuleCodes() {
        const values = []
        for (let index = 0; index < moduleModel.count; index += 1) {
            const option = moduleModel.get(index)
            if (option.selected) {
                values.push(option.value)
            }
        }
        return values
    }

    function _reloadOptionModel(model, options) {
        model.clear()
        model.append({ label: "Not set", value: "" })
        for (let index = 0; index < options.length; index += 1) {
            const option = options[index]
            model.append({ label: option.label || "", value: option.value || "" })
        }
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

    ListModel { id: moduleModel }
    ListModel { id: countryModel }
    ListModel { id: timezoneModel }
    ListModel { id: currencyModel }

    GridLayout {
        id: formGrid
        Layout.fillWidth: true
        columns: formGrid.width >= 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        // ── GENERAL ──────────────────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "General"
        }

        AppWidgets.CodeFieldRow {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Organization Code"
            value: root.organizationCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            onValueEdited: function(code) { root.organizationCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("organization", root.formData)
                    if (suggested && suggested.length > 0) {
                        root.organizationCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Display Name"
            required: true

            AppControls.TextField {
                id: displayNameField
                Layout.fillWidth: true
                placeholderText: "e.g. Acme Industrial Group"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Legal Name"
            helperText: "Full registered legal entity name, if different from the display name."

            AppControls.TextField {
                id: legalNameField
                Layout.fillWidth: true
                placeholderText: "e.g. Acme Industrial Group B.V."
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Timezone"

            AppControls.ComboBox {
                id: timezoneCombo
                Layout.fillWidth: true
                model: timezoneModel
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Base Currency"

            AppControls.ComboBox {
                id: currencyCombo
                Layout.fillWidth: true
                model: currencyModel
                textRole: "label"
            }
        }

        // ── LEGAL ────────────────────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Legal"
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Registration Number"

            AppControls.TextField {
                id: registrationNumberField
                Layout.fillWidth: true
                placeholderText: "e.g. company registration number"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Tax / VAT ID"

            AppControls.TextField {
                id: taxIdField
                Layout.fillWidth: true
                placeholderText: "e.g. tax or VAT identifier"
            }
        }

        // ── REGISTERED ADDRESS ──────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Registered Address"
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
                placeholderText: "Suite, floor, etc. (optional)"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Postal Code"

            AppControls.TextField {
                id: postalCodeField
                Layout.fillWidth: true
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "City"

            AppControls.TextField {
                id: cityField
                Layout.fillWidth: true
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "State / Region"

            AppControls.TextField {
                id: stateRegionField
                Layout.fillWidth: true
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Country"

            AppControls.ComboBox {
                id: countryCombo
                Layout.fillWidth: true
                model: countryModel
                textRole: "label"
            }
        }

        // ── CONTACT ──────────────────────────────────────────────────────
        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Contact"
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Email"

            AppControls.TextField {
                id: emailField
                Layout.fillWidth: true
                placeholderText: "e.g. contact@example.com"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Phone"

            AppControls.TextField {
                id: phoneField
                Layout.fillWidth: true
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            label: "Website"

            AppControls.TextField {
                id: websiteField
                Layout.fillWidth: true
                placeholderText: "e.g. https://www.example.com"
            }
        }

        // ── INITIAL MODULES (create only) ──────────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            visible: root.mode === "create"
            spacing: Theme.AppTheme.spacingSm

            AppWidgets.SectionHeading {
                Layout.fillWidth: true
                label: "Initial Modules"
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Choose the modules available immediately after organization provisioning."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: moduleModel

                delegate: AppControls.CheckBox {
                    required property int index
                    required property string label
                    required property bool selected

                    text: label
                    checked: selected
                    onToggled: moduleModel.setProperty(index, "selected", checked)
                }
            }
        }
    }
}
