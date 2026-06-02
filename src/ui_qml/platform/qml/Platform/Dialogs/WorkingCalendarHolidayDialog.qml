import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 560
    title: "Add Calendar Exception"
    primaryText: "Add Exception"
    primaryIcon: "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property var formData: ({
        holidayDate: holidayDateField.text.trim(),
        name: holidayNameField.text.trim()
    })

    function openForCreate() {
        holidayDateField.text = ""
        holidayNameField.text = ""
        open()
    }

    function submitDialog() {
        if (holidayDateField.text.trim().length === 0) {
            root.errorMessage = "Holiday date is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.formData)
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Holiday Date"
        required: true

        AppControls.DateField {
            id: holidayDateField
            Layout.fillWidth: true
            placeholderText: "YYYY-MM-DD"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Exception Name"

        AppControls.TextField {
            id: holidayNameField
            Layout.fillWidth: true
            placeholderText: "e.g. Company Shutdown"
        }
    }
}
