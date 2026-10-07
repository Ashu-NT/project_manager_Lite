import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers

// Recurrence intent is collected here as plain editor state (frequency/
// interval/byDay/...); the actual RFC5545 RRULE string is always produced
// by the one shared translation service (recurrence_text.py, reached via
// workspaceController.buildCalendarRecurrenceRule/parseCalendarRecurrenceRule
// /calendarRecurrenceSummary) -- this dialog never constructs or parses an
// RRULE string itself.
AppWidgets.EntityDialog {
    id: root

    property string calendarId: ""
    property var calendarOptions: []
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property string _mode: "create"
    property string _eventId: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthWide
    title: root._mode === "edit" ? "Edit Recurring Event" : "Add Recurring Event"
    primaryText: root._mode === "edit" ? "Save" : "Add"
    primaryIcon: root._mode === "edit" ? "save" : "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function _humanize(value) {
        return String(value || "").replace(/_/g, " ").replace(/\w\S*/g, function(word) {
            return word.charAt(0).toUpperCase() + word.substring(1).toLowerCase()
        })
    }
    function _trimmed(value) {
        return String(value === undefined || value === null ? "" : value).trim()
    }
    function _indexOfValue(options, value) {
        for (let i = 0; i < options.length; i += 1) {
            if (options[i].value === value) return i
        }
        return 0
    }

    readonly property var _eventTypes: [
        "MEETING", "TRAINING", "ADMIN", "MAINTENANCE",
        "UNAVAILABLE", "ON_CALL", "OVERTIME_WINDOW", "SHIFT_BLOCK"
    ].map(function(value) { return { "value": value, "label": root._humanize(value) } })
    readonly property var _impactTypes: [
        "UNAVAILABLE", "REDUCED_CAPACITY", "EXTRA_CAPACITY", "WORKING", "INFORMATION_ONLY"
    ].map(function(value) { return { "value": value, "label": root._humanize(value) } })
    readonly property var _repeatsOptions: [
        { "value": "DAILY", "label": "Daily" },
        { "value": "WEEKLY", "label": "Weekly" },
        { "value": "EVERY_WEEKDAY", "label": "Every weekday" },
        { "value": "MONTHLY", "label": "Monthly" },
        { "value": "YEARLY", "label": "Yearly" }
    ]
    readonly property var _weekdays: [
        { "code": "MO", "label": "Mon" }, { "code": "TU", "label": "Tue" }, { "code": "WE", "label": "Wed" },
        { "code": "TH", "label": "Thu" }, { "code": "FR", "label": "Fri" }, { "code": "SA", "label": "Sat" },
        { "code": "SU", "label": "Sun" }
    ]
    readonly property var _nthOptions: [
        { "value": 1, "label": "First" }, { "value": 2, "label": "Second" }, { "value": 3, "label": "Third" },
        { "value": 4, "label": "Fourth" }, { "value": -1, "label": "Last" }
    ]

    // ---- Visual recurrence builder state (the single source of truth the
    // RRULE is generated from -- see recurrence_text.py for the shape) ----
    property string _frequency: "WEEKLY"
    property int _interval: 1
    property var _byDay: []
    property string _monthlyMode: "DAY_OF_MONTH"
    property int _dayOfMonth: 1
    property int _nth: 1
    property string _nthWeekday: "MO"
    property bool _endsNever: true
    property bool _useAdvancedRule: false

    function _currentEditorState() {
        return {
            "frequency": root._frequency, "interval": root._interval, "byDay": root._byDay,
            "monthlyMode": root._monthlyMode, "dayOfMonth": root._dayOfMonth,
            "nth": root._nth, "nthWeekday": root._nthWeekday
        }
    }

    readonly property var _builtRule: root.workspaceController
        ? root.workspaceController.buildCalendarRecurrenceRule(root._currentEditorState())
        : ({ "ok": false, "rrule": "", "errorMessage": "" })
    readonly property string _effectiveRecurrenceRule: root._useAdvancedRule
        ? root._trimmed(advancedRuleField.text)
        : (root._builtRule.ok ? root._builtRule.rrule : "")
    readonly property string _summaryText: {
        if (root._effectiveRecurrenceRule.length === 0) return ""
        if (!root.workspaceController) return root._effectiveRecurrenceRule
        return root.workspaceController.calendarRecurrenceSummary(
            root._effectiveRecurrenceRule, root._trimmed(effectiveFromField.text)
        )
    }

    function _syncWeekdayChips() {
        for (let i = 0; i < root._weekdays.length; i += 1) {
            const item = weekdayRepeater.itemAt(i)
            if (item) item.checked = root._byDay.indexOf(root._weekdays[i].code) >= 0
        }
    }

    function _selectedCalendarId() {
        const option = root.calendarOptions[calendarCombo.currentIndex] || {}
        return String(option.value || option.id || root.calendarId || "")
    }
    function _calendarIndex(calendarId) {
        const value = String(calendarId || "")
        for (let index = 0; index < root.calendarOptions.length; index += 1) {
            const option = root.calendarOptions[index] || {}
            if (String(option.value || option.id || "") === value) return index
        }
        return root.calendarOptions.length > 0 ? 0 : -1
    }

    readonly property var _formData: ({
        calendarId: root._selectedCalendarId(),
        eventId: root._eventId,
        title: root._trimmed(titleField.text),
        eventType: (root._eventTypes[eventTypeCombo.currentIndex] || {}).value || "MEETING",
        recurrenceRule: root._effectiveRecurrenceRule,
        startTime: root._trimmed(startTimeField.text),
        endTime: root._trimmed(endTimeField.text),
        impactType: (root._impactTypes[impactCombo.currentIndex] || {}).value || "UNAVAILABLE",
        effectiveFrom: root._trimmed(effectiveFromField.text),
        effectiveTo: root._endsNever ? "" : root._trimmed(effectiveToField.text),
        capacityImpactPercent: root._trimmed(capacityField.text).length > 0
            ? parseFloat(root._trimmed(capacityField.text)) : 0.0
    })

    function _resetBuilderToDefault() {
        root._frequency = "WEEKLY"
        root._interval = 1
        root._byDay = []
        root._monthlyMode = "DAY_OF_MONTH"
        root._dayOfMonth = 1
        root._nth = 1
        root._nthWeekday = "MO"
        root._useAdvancedRule = false
    }

    function openForCreate(calId) {
        root._mode = "create"
        root._eventId = ""
        root.calendarId = calId || ""
        calendarCombo.currentIndex = root._calendarIndex(root.calendarId)
        titleField.text = ""
        eventTypeCombo.currentIndex = 0
        impactCombo.currentIndex = 0
        startTimeField.text = "09:00"
        endTimeField.text = "10:00"
        effectiveFromField.text = ""
        effectiveToField.text = ""
        capacityField.text = ""
        root._resetBuilderToDefault()
        repeatsCombo.currentIndex = root._indexOfValue(root._repeatsOptions, root._frequency)
        intervalSpin.value = root._interval
        dayOfMonthSpin.value = root._dayOfMonth
        nthCombo.currentIndex = root._indexOfValue(root._nthOptions, root._nth)
        nthWeekdayCombo.currentIndex = root._indexOfValue(root._weekdays.map(function(w) { return { "value": w.code } }), root._nthWeekday)
        dayOfMonthRadio.checked = true
        endsNeverRadio.checked = true
        advancedRuleField.text = ""
        root._syncWeekdayChips()
        open()
    }

    function openForEdit(calId, eventState) {
        const state = eventState || {}
        root._mode = "edit"
        root._eventId = String(state.id || "")
        root.calendarId = calId || ""
        calendarCombo.currentIndex = root._calendarIndex(root.calendarId)
        titleField.text = String(state.title || "")
        eventTypeCombo.currentIndex = root._indexOfValue(root._eventTypes, String(state.eventType || ""))
        impactCombo.currentIndex = root._indexOfValue(root._impactTypes, String(state.impactType || ""))
        startTimeField.text = String(state.startTimeLabel || "")
        endTimeField.text = String(state.endTimeLabel || "")
        effectiveFromField.text = String(state.effectiveFrom || "")
        const hasEnd = String(state.effectiveTo || "").length > 0
        effectiveToField.text = String(state.effectiveTo || "")
        capacityField.text = state.capacityImpactPercent ? String(state.capacityImpactPercent) : ""

        const existingRule = String(state.recurrenceRule || "")
        const parsed = root.workspaceController ? root.workspaceController.parseCalendarRecurrenceRule(existingRule) : { "ok": false }
        if (parsed && parsed.ok) {
            root._frequency = parsed.frequency
            root._interval = parsed.interval
            root._byDay = parsed.byDay || []
            root._monthlyMode = parsed.monthlyMode
            root._dayOfMonth = parsed.dayOfMonth
            root._nth = parsed.nth
            root._nthWeekday = parsed.nthWeekday
            root._useAdvancedRule = false
        } else {
            // Doesn't match a shape the visual builder produces -- never
            // silently reinterpret or discard it; the raw rule stays
            // editable (and visible) in the Advanced field instead.
            root._resetBuilderToDefault()
            root._useAdvancedRule = true
        }
        repeatsCombo.currentIndex = root._indexOfValue(root._repeatsOptions, root._frequency)
        intervalSpin.value = root._interval
        dayOfMonthSpin.value = root._dayOfMonth
        nthCombo.currentIndex = root._indexOfValue(root._nthOptions, root._nth)
        nthWeekdayCombo.currentIndex = root._indexOfValue(root._weekdays.map(function(w) { return { "value": w.code } }), root._nthWeekday)
        if (root._monthlyMode === "NTH_WEEKDAY") nthWeekdayRadio.checked = true
        else dayOfMonthRadio.checked = true
        if (hasEnd) endsOnDateRadio.checked = true
        else endsNeverRadio.checked = true
        advancedRuleField.text = existingRule
        root._syncWeekdayChips()
        open()
    }

    function submitDialog() {
        if (root._selectedCalendarId().length === 0) {
            root.errorMessage = "Calendar is required."
            return
        }
        if (root._trimmed(titleField.text).length === 0) {
            root.errorMessage = "Title is required."
            return
        }
        if (root._effectiveRecurrenceRule.length === 0) {
            root.errorMessage = root._useAdvancedRule
                ? "Recurrence rule is required."
                : (root._builtRule.errorMessage || "Recurrence is required.")
            return
        }
        if (root._trimmed(effectiveFromField.text).length === 0) {
            root.errorMessage = "Starts date is required (YYYY-MM-DD)."
            return
        }
        if (!root._endsNever && root._trimmed(effectiveToField.text).length === 0) {
            root.errorMessage = "Choose an end date, or select \"Never\"."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root._mode, root._formData)
    }

    onCalendarOptionsChanged: {
        calendarCombo.currentIndex = root._calendarIndex(root._selectedCalendarId())
    }

    // ---- Body ----

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
        label: "Title"
        required: true
        AppControls.TextField {
            id: titleField
            objectName: "recurringTitleField"
            Layout.fillWidth: true
            placeholderText: "e.g. Weekly Team Standup"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Event Type"
            required: true
            AppControls.ComboBox {
                id: eventTypeCombo
                Layout.fillWidth: true
                model: root._eventTypes
                textRole: "label"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Impact"
            required: true
            AppControls.ComboBox {
                id: impactCombo
                Layout.fillWidth: true
                model: root._impactTypes
                textRole: "label"
            }
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        Layout.topMargin: Theme.AppTheme.spacingSm
        text: "RECURRENCE"
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.typeMetadataSize
        font.weight: Theme.AppTheme.weightSemibold
        font.letterSpacing: 0.5
    }

    ColumnLayout {
        Layout.fillWidth: true
        visible: !root._useAdvancedRule
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Repeats"
            required: true
            AppControls.ComboBox {
                id: repeatsCombo
                objectName: "recurringRepeatsCombo"
                Layout.fillWidth: true
                model: root._repeatsOptions
                textRole: "label"
                onActivated: function(index) { root._frequency = root._repeatsOptions[index].value }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root._frequency !== "EVERY_WEEKDAY"
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label { text: "Every"; color: Theme.AppTheme.textPrimary }
            SpinBox {
                id: intervalSpin
                objectName: "recurringIntervalSpin"
                from: 1
                to: 99
                onValueModified: root._interval = value
            }
            AppControls.Label {
                text: root._frequency === "DAILY" ? "day(s)"
                    : root._frequency === "WEEKLY" ? "week(s)"
                    : root._frequency === "MONTHLY" ? "month(s)"
                    : "year(s)"
                color: Theme.AppTheme.textPrimary
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root._frequency === "WEEKLY"
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text: "Repeat on"
                color: Theme.AppTheme.textSecondary
                font.pixelSize: Theme.AppTheme.captionSize
            }
            RowLayout {
                spacing: Theme.AppTheme.spacingXs
                Repeater {
                    id: weekdayRepeater
                    objectName: "recurringWeekdayRepeater"
                    model: root._weekdays
                    delegate: AppControls.ChoiceChip {
                        required property var modelData
                        text: modelData.label
                        onCheckedChanged: {
                            const code = modelData.code
                            const idx = root._byDay.indexOf(code)
                            if (checked && idx < 0) {
                                const next = root._byDay.slice()
                                next.push(code)
                                root._byDay = next
                            } else if (!checked && idx >= 0) {
                                const next = root._byDay.slice()
                                next.splice(idx, 1)
                                root._byDay = next
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root._frequency === "MONTHLY"
            spacing: Theme.AppTheme.spacingXs

            RowLayout {
                spacing: Theme.AppTheme.spacingSm
                AppControls.RadioButton {
                    id: dayOfMonthRadio
                    objectName: "recurringDayOfMonthRadio"
                    text: "On day"
                    onCheckedChanged: if (checked) root._monthlyMode = "DAY_OF_MONTH"
                }
                SpinBox {
                    id: dayOfMonthSpin
                    from: 1
                    to: 31
                    enabled: root._monthlyMode === "DAY_OF_MONTH"
                    onValueModified: root._dayOfMonth = value
                }
            }
            RowLayout {
                spacing: Theme.AppTheme.spacingSm
                AppControls.RadioButton {
                    id: nthWeekdayRadio
                    objectName: "recurringNthWeekdayRadio"
                    text: "On the"
                    onCheckedChanged: if (checked) root._monthlyMode = "NTH_WEEKDAY"
                }
                AppControls.ComboBox {
                    id: nthCombo
                    objectName: "recurringNthCombo"
                    model: root._nthOptions
                    textRole: "label"
                    enabled: root._monthlyMode === "NTH_WEEKDAY"
                    onActivated: function(index) { root._nth = root._nthOptions[index].value }
                }
                AppControls.ComboBox {
                    id: nthWeekdayCombo
                    objectName: "recurringNthWeekdayCombo"
                    model: root._weekdays
                    textRole: "label"
                    enabled: root._monthlyMode === "NTH_WEEKDAY"
                    onActivated: function(index) { root._nthWeekday = root._weekdays[index].code }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.FormField {
                Layout.fillWidth: true
                label: "Starts"
                required: true
                AppControls.DateField {
                    id: effectiveFromField
                    objectName: "recurringStartsField"
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }

            AppWidgets.FormField {
                Layout.fillWidth: true
                label: "Ends"
                ColumnLayout {
                    spacing: Theme.AppTheme.spacingXs
                    RowLayout {
                        spacing: Theme.AppTheme.spacingSm
                        AppControls.RadioButton {
                            id: endsNeverRadio
                            objectName: "recurringEndsNeverRadio"
                            text: "Never"
                            onCheckedChanged: if (checked) root._endsNever = true
                        }
                        AppControls.RadioButton {
                            id: endsOnDateRadio
                            objectName: "recurringEndsOnDateRadio"
                            text: "On date"
                            onCheckedChanged: if (checked) root._endsNever = false
                        }
                    }
                    AppControls.DateField {
                        id: effectiveToField
                        Layout.fillWidth: true
                        enabled: !root._endsNever
                        placeholderText: "YYYY-MM-DD"
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Summary"
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs
                AppIcons.AppIcon {
                    name: "calendar"
                    size: Theme.AppTheme.iconSm
                    iconColor: Theme.AppTheme.textSecondary
                }
                AppControls.Label {
                    Layout.fillWidth: true
                    text: root._summaryText.length > 0 ? root._summaryText : "Choose a recurrence above"
                    color: Theme.AppTheme.textSecondary
                    elide: Text.ElideRight
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs
            AppIcons.AppIcon {
                name: root._useAdvancedRule ? "chevron_down" : "chevron_right"
                size: Theme.AppTheme.iconXs
                iconColor: Theme.AppTheme.textMuted
            }
            AppControls.Label {
                text: "Advanced recurrence"
                color: Theme.AppTheme.textMuted
                font.pixelSize: Theme.AppTheme.captionSize
            }
            Item { Layout.fillWidth: true }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root._useAdvancedRule = !root._useAdvancedRule
            }
        }
    }

    // Normal users manage recurrence entirely through the visual builder
    // above; this stays collapsed/opt-in, and is the only path for a
    // persisted rule this builder can't represent (see openForEdit).
    ColumnLayout {
        Layout.fillWidth: true
        visible: root._useAdvancedRule
        spacing: Theme.AppTheme.spacingXs

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "RRULE"
            required: true
            AppControls.TextField {
                id: advancedRuleField
                objectName: "recurringAdvancedRuleField"
                Layout.fillWidth: true
                placeholderText: "FREQ=WEEKLY;BYDAY=MO"
            }
        }
        AppControls.Label {
            Layout.fillWidth: true
            text: root._summaryText.length > 0 ? root._summaryText : ""
            color: Theme.AppTheme.textMuted
            font.pixelSize: Theme.AppTheme.captionSize
            wrapMode: Text.WrapAnywhere
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
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Capacity Impact %"
            AppControls.TextField {
                id: capacityField
                Layout.fillWidth: true
                placeholderText: "Optional"
            }
        }
    }
}
