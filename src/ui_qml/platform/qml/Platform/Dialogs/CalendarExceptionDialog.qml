import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string calendarId: ""
    property var draft: ({})

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 620
    title: "Add Calendar Exception"
    primaryText: "Add"
    primaryIcon: "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property var _exceptionTypes: [
        "HOLIDAY", "SHUTDOWN", "VACATION", "SICK_LEAVE", "TRAINING",
        "MEETING", "NON_WORKING", "EXTRA_WORKING", "REDUCED_HOURS",
        "OVERTIME", "MAINTENANCE_WINDOW", "SITE_CLOSED"
    ]
    readonly property var _impactTypes: [
        "UNAVAILABLE", "REDUCED_CAPACITY", "EXTRA_CAPACITY", "WORKING", "INFORMATION_ONLY"
    ]

    readonly property var _formData: ({
        calendarId: root.calendarId,
        exceptionDate: dateField.text.trim(),
        exceptionType: exTypeCombo.currentText || "HOLIDAY",
        name: nameField.text.trim(),
        impactType: impactCombo.currentText || "UNAVAILABLE",
        description: descField.text.trim(),
        hoursOverride: hoursField.text.trim().length > 0 ? parseFloat(hoursField.text.trim()) : 0.0
    })

    function openForCreate(calId) {
        root.calendarId = calId || ""
        root.draft = {}
        dateField.text = ""
        nameField.text = ""
        exTypeCombo.currentIndex = 0
        impactCombo.currentIndex = 0
        descField.text = ""
        hoursField.text = ""
        open()
    }

    function submitDialog() {
        if (dateField.text.trim().length === 0) {
            root.errorMessage = "Exception date is required (YYYY-MM-DD)."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Exception name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root._formData)
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Exception Date"
        required: true

        AppControls.DateField {
            id: dateField
            Layout.fillWidth: true
            placeholderText: "YYYY-MM-DD"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Name"
        required: true

        AppControls.TextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "e.g. Christmas Day"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Exception Type"
        required: true

        AppControls.ComboBox {
            id: exTypeCombo
            Layout.fillWidth: true
            model: root._exceptionTypes
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Impact Type"
        required: true

        AppControls.ComboBox {
            id: impactCombo
            Layout.fillWidth: true
            model: root._impactTypes
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Hours Override"

        AppControls.TextField {
            id: hoursField
            Layout.fillWidth: true
            placeholderText: "Leave blank to use full-day impact"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"

        AppControls.TextField {
            id: descField
            Layout.fillWidth: true
            placeholderText: "Optional"
        }
    }
}
