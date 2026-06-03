import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string calendarId: ""

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 660
    title: "Add Recurring Event"
    primaryText: "Add"
    primaryIcon: "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property var _eventTypes: [
        "MEETING", "TRAINING", "ADMIN", "MAINTENANCE",
        "UNAVAILABLE", "ON_CALL", "OVERTIME_WINDOW", "SHIFT_BLOCK"
    ]
    readonly property var _impactTypes: [
        "UNAVAILABLE", "REDUCED_CAPACITY", "EXTRA_CAPACITY", "WORKING", "INFORMATION_ONLY"
    ]
    readonly property var _commonRules: [
        "FREQ=WEEKLY;BYDAY=MO",
        "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        "FREQ=WEEKLY;BYDAY=MO,WE,FR",
        "FREQ=DAILY",
        "FREQ=MONTHLY;BYDAY=1MO"
    ]

    readonly property var _formData: ({
        calendarId: root.calendarId,
        title: titleField.text.trim(),
        eventType: eventTypeCombo.currentText || "MEETING",
        recurrenceRule: rruleField.text.trim(),
        startTime: startTimeField.text.trim(),
        endTime: endTimeField.text.trim(),
        impactType: impactCombo.currentText || "UNAVAILABLE",
        effectiveFrom: effectiveFromField.text.trim(),
        effectiveTo: effectiveToField.text.trim()
    })

    function openForCreate(calId) {
        root.calendarId = calId || ""
        titleField.text = ""
        eventTypeCombo.currentIndex = 0
        rruleField.text = "FREQ=WEEKLY;BYDAY=MO"
        startTimeField.text = "09:00"
        endTimeField.text = "10:00"
        impactCombo.currentIndex = 0
        effectiveFromField.text = ""
        effectiveToField.text = ""
        open()
    }

    function submitDialog() {
        if (titleField.text.trim().length === 0) {
            root.errorMessage = "Title is required."
            return
        }
        if (rruleField.text.trim().length === 0) {
            root.errorMessage = "Recurrence rule is required."
            return
        }
        if (effectiveFromField.text.trim().length === 0) {
            root.errorMessage = "Effective from date is required (YYYY-MM-DD)."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root._formData)
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Title"
        required: true

        AppControls.TextField {
            id: titleField
            Layout.fillWidth: true
            placeholderText: "e.g. Weekly Team Standup"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Event Type"
        required: true

        AppControls.ComboBox {
            id: eventTypeCombo
            Layout.fillWidth: true
            model: root._eventTypes
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
        label: "Recurrence Rule (RRULE)"
        required: true

        AppControls.ComboBox {
            id: rruleField
            Layout.fillWidth: true
            editable: true
            model: root._commonRules
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Start Time"
            required: true

            AppControls.TextField {
                id: startTimeField
                Layout.fillWidth: true
                placeholderText: "HH:MM"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "End Time"
            required: true

            AppControls.TextField {
                id: endTimeField
                Layout.fillWidth: true
                placeholderText: "HH:MM"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Effective From"
            required: true

            AppControls.DateField {
                id: effectiveFromField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Effective To"

            AppControls.DateField {
                id: effectiveToField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD (optional)"
            }
        }
    }
}
