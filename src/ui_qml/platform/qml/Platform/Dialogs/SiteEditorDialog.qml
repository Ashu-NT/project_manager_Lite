import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    title: root.mode === "create" ? "New Site" : "Edit Site"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onAccepted: root.saveRequested(root.mode, root.formData)
    onRejected: root.close()

    readonly property var formData: ({
        siteId: root.draft.siteId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        siteCode: siteCodeField.text.trim(),
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
        siteCodeField.text = root.draft.siteCode || ""
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

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: siteCodeField

            Layout.preferredWidth: 180
            placeholderText: "Site code"
        }

        AppControls.TextField {
            id: nameField

            Layout.fillWidth: true
            placeholderText: "Site name"
        }
    }

    AppControls.TextField {
        id: descriptionField

        Layout.fillWidth: true
        placeholderText: "Description"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: cityField

            Layout.fillWidth: true
            placeholderText: "City"
        }

        AppControls.TextField {
            id: countryField

            Layout.fillWidth: true
            placeholderText: "Country"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: timezoneField

            Layout.fillWidth: true
            placeholderText: "Timezone"
        }

        AppControls.TextField {
            id: currencyField

            Layout.preferredWidth: 120
            placeholderText: "Currency"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: siteTypeField

            Layout.fillWidth: true
            placeholderText: "Site type"
        }

        AppControls.TextField {
            id: statusField

            Layout.fillWidth: true
            placeholderText: "Status"
        }
    }

    AppControls.TextArea {
        id: notesField

        Layout.fillWidth: true
        Layout.preferredHeight: 96
        placeholderText: "Notes"
        wrapMode: TextEdit.WordWrap
    }

    AppControls.CheckBox {
        id: activeCheck

        text: "Active site"
    }
}
