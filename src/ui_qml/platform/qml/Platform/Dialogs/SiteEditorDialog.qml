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

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
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
        city: cityField.text.trim(),
        country: countryField.text.trim(),
        timezoneName: timezoneField.text.trim(),
        currencyCode: currencyField.text.trim().toUpperCase(),
        siteType: siteTypeField.text.trim(),
        status: statusField.text.trim(),
        notes: notesField.text.trim(),
        isActive: activeCheck.checked
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
        cityField.text = root.draft.city || ""
        countryField.text = root.draft.country || ""
        timezoneField.text = root.draft.timezoneName || ""
        currencyField.text = root.draft.currencyCode || ""
        siteTypeField.text = root.draft.siteType || ""
        statusField.text = root.draft.status || ""
        notesField.text = root.draft.notes || ""
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
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

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

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

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

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
            label: "Status"

            AppControls.TextField {
                id: statusField
                Layout.fillWidth: true
                placeholderText: "e.g. Operational"
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
            placeholderText: "Operational notes or context"
            wrapMode: TextEdit.WordWrap
        }
    }

    AppControls.CheckBox {
        id: activeCheck

        text: "Active site"
    }
}
