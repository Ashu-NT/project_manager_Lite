import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var workspaceController: null
    property string siteCode: ""
    property string organizationName: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthStandard
    title: root.mode === "create" ? "New Site" : "Edit Site"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (root.siteCode.trim().length === 0) {
            root.errorMessage = "Site code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Site name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    readonly property var formData: ({
        siteId: root.draft.siteId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        siteCode: root.siteCode.trim(),
        name: nameField.text.trim(),
        description: descriptionField.text.trim(),
        addressLine1: addressLine1Field.text.trim(),
        addressLine2: addressLine2Field.text.trim(),
        city: cityField.text.trim(),
        region: regionField.text.trim(),
        postalCode: postalCodeField.text.trim(),
        country: countryField.text.trim(),
        timezoneName: timezoneField.text.trim(),
        currencyCode: currencyField.text.trim().toUpperCase(),
        siteType: siteTypeField.text.trim(),
        notes: notesField.text.trim()
    })

    function openForCreate() {
        root.mode = "create"
        root.draft = ({})
        _loadDraft()
        open()
    }

    function openForEdit(draftData) {
        root.mode = "edit"
        root.draft = draftData || ({})
        _loadDraft()
        open()
    }

    function _loadDraft() {
        root.siteCode = root.draft.siteCode || ""
        nameField.text = root.draft.name || ""
        descriptionField.text = root.draft.description || ""
        addressLine1Field.text = root.draft.addressLine1 || ""
        addressLine2Field.text = root.draft.addressLine2 || ""
        cityField.text = root.draft.city || ""
        regionField.text = root.draft.region || ""
        postalCodeField.text = root.draft.postalCode || ""
        countryField.text = root.draft.country || ""
        timezoneField.text = root.draft.timezoneName || ""
        currencyField.text = root.draft.currencyCode || ""
        siteTypeField.text = root.draft.siteType || ""
        notesField.text = root.draft.notes || ""
    }

    AppWidgets.CodeFieldRow {
        Layout.fillWidth: true
        label: "Site Code"
        value: root.siteCode
        placeholderText: "Auto-generated if empty"
        required: true
        generateVisible: true
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onValueEdited: function(code) { root.siteCode = code }
        onGenerateRequested: {
            if (root.workspaceController) {
                const suggested = root.workspaceController.generateEntityCode("site", root.formData)
                if (suggested && suggested.length > 0) {
                    root.siteCode = suggested
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Organization"

        AppControls.Label {
            Layout.fillWidth: true
            text: root.organizationName || "Active organization"
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Site Name"
        required: true

        AppControls.TextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "e.g. North Plant"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"

        AppControls.TextField {
            id: descriptionField
            Layout.fillWidth: true
            placeholderText: "Short description of the site"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Address Line 1"

        AppControls.TextField {
            id: addressLine1Field
            Layout.fillWidth: true
            placeholderText: "Street address"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Address Line 2"

        AppControls.TextField {
            id: addressLine2Field
            Layout.fillWidth: true
            placeholderText: "Suite, building, unit (optional)"
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
                placeholderText: "e.g. 3011"
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

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "State / Region"

            AppControls.TextField {
                id: regionField
                Layout.fillWidth: true
                placeholderText: "e.g. South Holland"
            }
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
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Timezone"

            AppControls.TextField {
                id: timezoneField
                Layout.fillWidth: true
                placeholderText: "e.g. Europe/Amsterdam"
            }
        }

        AppWidgets.FormField {
            Layout.preferredWidth: 140
            label: "Currency"

            AppControls.TextField {
                id: currencyField
                Layout.fillWidth: true
                placeholderText: "e.g. EUR"
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Site Type"

        AppControls.TextField {
            id: siteTypeField
            Layout.fillWidth: true
            placeholderText: "e.g. Refinery"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"

        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            placeholderText: "Operational notes or context"
            wrapMode: TextEdit.WordWrap
        }
    }
}
