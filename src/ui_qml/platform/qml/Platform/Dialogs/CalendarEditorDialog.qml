import QtQuick
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
    width: 640
    title: root.mode === "create" ? "New Calendar" : "Edit Calendar"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property var _calendarTypes: [
        "GLOBAL", "SITE", "DEPARTMENT", "EMPLOYEE", "PROJECT", "RESOURCE"
    ]
    readonly property var _formData: ({
        calendarId: root.draft.id || "",
        code: codeField.text.trim(),
        name: nameField.text.trim(),
        calendarType: typeCombo.currentText || "GLOBAL",
        timezone: timezoneField.text.trim() || "UTC",
        description: descField.text.trim(),
        isDefault: defaultCheck.checked
    })

    function openForCreate() {
        root.mode = "create"
        root.draft = {}
        codeField.text = ""
        nameField.text = ""
        typeCombo.currentIndex = 0
        timezoneField.text = "UTC"
        descField.text = ""
        defaultCheck.checked = false
        open()
    }

    function openForEdit(draftData) {
        root.mode = "edit"
        root.draft = draftData || {}
        codeField.text = String(root.draft.code || "")
        nameField.text = String(root.draft.name || "")
        const typeIdx = root._calendarTypes.indexOf(root.draft.calendarType || "GLOBAL")
        typeCombo.currentIndex = typeIdx >= 0 ? typeIdx : 0
        timezoneField.text = String(root.draft.timezone || "UTC")
        descField.text = String(root.draft.description || "")
        defaultCheck.checked = root.draft.isDefault === true
        open()
    }

    function submitDialog() {
        if (codeField.text.trim().length === 0) {
            root.errorMessage = "Calendar code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Calendar name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root._formData)
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Code"
        required: true

        AppControls.TextField {
            id: codeField
            Layout.fillWidth: true
            placeholderText: "e.g. SITE-HH"
            readOnly: root.mode === "edit"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Name"
        required: true

        AppControls.TextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "e.g. Hamburg Site Calendar"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Calendar Type"
        required: true

        AppControls.ComboBox {
            id: typeCombo
            Layout.fillWidth: true
            model: root._calendarTypes
            enabled: root.mode === "create"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Timezone"

        AppControls.TextField {
            id: timezoneField
            Layout.fillWidth: true
            placeholderText: "e.g. Europe/Berlin"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"

        AppControls.TextField {
            id: descField
            Layout.fillWidth: true
            placeholderText: "Optional description"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Default Calendar"

        AppControls.CheckBox {
            id: defaultCheck
            text: "Mark as default for its type"
        }
    }
}
