import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string entityType: ""
    property string entityId: ""
    property string entityLabel: ""
    property var availableCalendars: []

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 600
    title: "Assign Calendar"
    primaryText: "Assign"
    primaryIcon: "calendar"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property var _calendarNames: {
        const result = []
        const cals = root.availableCalendars || []
        for (let i = 0; i < cals.length; i++) {
            result.push(String(cals[i].name || cals[i].code || cals[i].id || ""))
        }
        return result
    }

    readonly property var _formData: ({
        entityType: root.entityType,
        entityId: root.entityId,
        calendarId: _resolveCalendarId(),
        effectiveFrom: effectiveFromField.text.trim(),
        effectiveTo: effectiveToField.text.trim(),
        isDefault: true,
        priority: 0
    })

    function _resolveCalendarId() {
        const idx = calendarCombo.currentIndex
        const cals = root.availableCalendars || []
        if (idx >= 0 && idx < cals.length) {
            return String(cals[idx].id || "")
        }
        return ""
    }

    function openForAssign(entityType, entityId, entityLabel, calendars) {
        root.entityType = entityType || ""
        root.entityId = entityId || ""
        root.entityLabel = entityLabel || ""
        root.availableCalendars = calendars || []
        calendarCombo.currentIndex = 0
        effectiveFromField.text = ""
        effectiveToField.text = ""
        open()
    }

    function submitDialog() {
        if (root._resolveCalendarId().length === 0) {
            root.errorMessage = "Select a calendar to assign."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root._formData)
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Entity"

        AppControls.TextField {
            Layout.fillWidth: true
            readOnly: true
            text: root.entityLabel.length > 0
                ? root.entityLabel + " (" + root.entityType + ")"
                : root.entityType
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Calendar"
        required: true

        AppControls.ComboBox {
            id: calendarCombo
            Layout.fillWidth: true
            model: root._calendarNames
        }
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        tone: "info"
        message: "Leave dates blank for an open-ended assignment. The calendar becomes effective immediately."
        visible: root._calendarNames.length > 0
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        tone: "warning"
        message: "No calendars are available. Create a calendar in Calendar Management first."
        visible: root._calendarNames.length === 0
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Effective From"

            AppControls.DateField {
                id: effectiveFromField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD (optional)"
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
