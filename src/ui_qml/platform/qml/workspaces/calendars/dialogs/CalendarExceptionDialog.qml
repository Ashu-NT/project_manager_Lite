import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string calendarId: ""
    property var calendarOptions: []
    property var draft: ({})
    property string _mode: "create"
    property string _exceptionId: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthWide
    title: root._mode === "edit" ? "Edit Calendar Exception" : "Add Calendar Exception"
    primaryText: root._mode === "edit" ? "Save" : "Add"
    primaryIcon: root._mode === "edit" ? "save" : "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    // {value, label} so the combo always submits the real backend enum
    // while displaying a humanized label -- never a raw enum string in the
    // UI (see serializers.py's _title_case_label for the matching
    // read-side convention).
    readonly property var _exceptionTypes: [
        "HOLIDAY", "SHUTDOWN", "VACATION", "SICK_LEAVE", "TRAINING",
        "MEETING", "NON_WORKING", "EXTRA_WORKING", "REDUCED_HOURS",
        "OVERTIME", "MAINTENANCE_WINDOW", "SITE_CLOSED"
    ].map(function(value) { return { "value": value, "label": root._humanize(value) } })
    readonly property var _impactTypes: [
        "UNAVAILABLE", "REDUCED_CAPACITY", "EXTRA_CAPACITY", "WORKING", "INFORMATION_ONLY"
    ].map(function(value) { return { "value": value, "label": root._humanize(value) } })

    function _humanize(value) {
        return String(value || "").replace(/_/g, " ").replace(/\w\S*/g, function(word) {
            return word.charAt(0).toUpperCase() + word.substring(1).toLowerCase()
        })
    }

    readonly property var _formData: ({
        calendarId: root._selectedCalendarId(),
        exceptionId: root._exceptionId,
        exceptionDate: dateField.text.trim(),
        exceptionType: (root._exceptionTypes[exTypeCombo.currentIndex] || {}).value || "HOLIDAY",
        name: nameField.text.trim(),
        impactType: (root._impactTypes[impactCombo.currentIndex] || {}).value || "UNAVAILABLE",
        description: descField.text.trim(),
        hoursOverride: hoursField.text.trim().length > 0 ? parseFloat(hoursField.text.trim()) : 0.0
    })

    function _selectedCalendarId() {
        const option = root.calendarOptions[calendarCombo.currentIndex] || {}
        return String(option.value || option.id || root.calendarId || "")
    }

    function _calendarIndex(calendarId) {
        const value = String(calendarId || "")
        for (let index = 0; index < root.calendarOptions.length; index += 1) {
            const option = root.calendarOptions[index] || {}
            if (String(option.value || option.id || "") === value)
                return index
        }
        return root.calendarOptions.length > 0 ? 0 : -1
    }

    function _indexOfValue(options, value) {
        for (let i = 0; i < options.length; i += 1) {
            if (options[i].value === value) return i
        }
        return 0
    }

    function openForCreate(calId, prefillDate) {
        root._mode = "create"
        root._exceptionId = ""
        root.calendarId = calId || ""
        root.draft = {}
        calendarCombo.currentIndex = root._calendarIndex(root.calendarId)
        dateField.text = prefillDate || ""
        dateField.enabled = true
        nameField.text = ""
        exTypeCombo.currentIndex = 0
        impactCombo.currentIndex = 0
        descField.text = ""
        hoursField.text = ""
        open()
    }

    function openForEdit(calId, exceptionState) {
        const state = exceptionState || {}
        root._mode = "edit"
        root._exceptionId = String(state.id || "")
        root.calendarId = calId || ""
        root.draft = state
        calendarCombo.currentIndex = root._calendarIndex(root.calendarId)
        dateField.text = String(state.exceptionDate || "")
        // The exception's own date is never editable after creation -- the
        // backend's ExceptionUpdateCommand doesn't accept a new date either
        // (see build_exception_update_command), so the field would silently
        // do nothing if left enabled.
        dateField.enabled = false
        nameField.text = String(state.name || "")
        exTypeCombo.currentIndex = root._indexOfValue(root._exceptionTypes, String(state.exceptionType || ""))
        impactCombo.currentIndex = root._indexOfValue(root._impactTypes, String(state.impactType || ""))
        descField.text = String(state.description || "")
        hoursField.text = state.hoursOverride ? String(state.hoursOverride) : ""
        open()
    }

    function submitDialog() {
        if (root._selectedCalendarId().length === 0) {
            root.errorMessage = "Calendar is required."
            return
        }
        if (root._mode === "create" && dateField.text.trim().length === 0) {
            root.errorMessage = "Exception date is required (YYYY-MM-DD)."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Exception name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root._mode, root._formData)
    }

    onCalendarOptionsChanged: {
        calendarCombo.currentIndex = root._calendarIndex(root._selectedCalendarId())
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Calendar"
        required: true

        AppControls.ComboBox {
            id: calendarCombo
            Layout.fillWidth: true
            model: root.calendarOptions
            textRole: "label"
        }
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
            textRole: "label"
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
            textRole: "label"
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
