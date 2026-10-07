pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Window
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import workspaces.calendars.sections.views.month 1.0 as CalendarMonth

// Calendar tab's "Month" view: the real operational-calendar surface,
// replacing the earlier interim placeholder. One bounded range request per
// visible month grid (including leading/trailing adjacent-month dates --
// the exact 42 cells QtQuick's own MonthGrid renders); every working/
// holiday/exception fact comes from that resolved response, never
// recalculated here. "Today" is the calendar's own business-local today
// (calendarBusinessToday), never a QML `new Date()`.
Item {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property string calendarId: ""
    property bool canWrite: true

    signal addExceptionRequested(string date)

    implicitHeight: _layout.implicitHeight

    property int _year: 0
    property int _month: 0
    property string _businessToday: ""
    property string _selectedDate: ""
    property var _daysByDate: ({})
    property bool _loading: false
    property string _errorMessage: ""
    property bool _initialized: false

    readonly property string _monthLabel: root._year > 0
        ? Qt.locale().standaloneMonthName(root._month) + " " + root._year
        : ""
    readonly property var _selectedDayData: root._selectedDate.length > 0
        ? (root._daysByDate[root._selectedDate] || null)
        : null
    readonly property bool _showInspector: root._selectedDayData !== null

    // Tone -> status chip presentation. Pure QML display mapping of the
    // already-resolved `tone` (see serialize_calendar_day_view) -- no
    // business logic, just which label/chip color represents each tone.
    readonly property var _statusByTone: ({
        "normal":      { "label": "Working Day", "tone": "success" },
        "nonWorking":  { "label": "Non-working",  "tone": "neutral" },
        "holiday":     { "label": "",             "tone": "info" },
        "unavailable": { "label": "",             "tone": "danger" },
        "reduced":     { "label": "",             "tone": "warning" },
        "extra":       { "label": "",             "tone": "success" },
        "info":        { "label": "",             "tone": "info" }
    })

    function _inspectorTitle(dayData) {
        return dayData ? String(dayData.dateLabel || "") : ""
    }

    function _inspectorStatusLabel(dayData) {
        if (!dayData) return ""
        const preset = root._statusByTone[String(dayData.tone || "normal")] || root._statusByTone.normal
        return preset.label.length > 0
            ? preset.label
            : (String(dayData.exceptionTypeLabel || "") || String(dayData.impactLabel || ""))
    }

    function _inspectorStatusTone(dayData) {
        if (!dayData) return "neutral"
        const preset = root._statusByTone[String(dayData.tone || "normal")] || root._statusByTone.normal
        return preset.tone
    }

    function _inspectorGroups(dayData) {
        if (!dayData) return []
        const groups = []
        const workingRows = dayData.isWorkingDay
            ? [
                { "label": "Hours", "value": (dayData.startTimeLabel && dayData.endTimeLabel)
                    ? (dayData.startTimeLabel + "–" + dayData.endTimeLabel) : "" },
                { "label": "Available", "value": dayData.availableHours > 0
                    ? (dayData.availableHours + " h") : "0 h" }
            ]
            : [{ "label": "Status", "value": "Non-working" }]
        groups.push({ "title": "Working Time", "rows": workingRows })

        if (String(dayData.exceptionTypeLabel || "").length > 0) {
            groups.push({
                "title": "Exception",
                "rows": [
                    { "label": "Type", "value": String(dayData.exceptionTypeLabel || "") },
                    { "label": "Impact", "value": String(dayData.impactLabel || "") },
                    { "label": "Name", "value": String(dayData.primaryLabel || "") }
                ]
            })
        }
        return groups
    }

    function _emptyDayData(dateIso) {
        return {
            "date": dateIso, "dayNumber": 0, "dateLabel": "", "isToday": false,
            "isWorkingDay": false, "availableHours": 0, "startTimeLabel": "",
            "endTimeLabel": "", "primaryLabel": "", "secondaryLabel": "",
            "exceptionTypeLabel": "", "impactLabel": "", "tone": "normal",
            "accessibilityLabel": dateIso
        }
    }

    function _isoDate(d) {
        const y = d.getFullYear()
        const m = String(d.getMonth() + 1).padStart(2, "0")
        const day = String(d.getDate()).padStart(2, "0")
        return y + "-" + m + "-" + day
    }

    // Grid-layout boundary math only (which 42 calendar days a standard
    // month grid displays) -- not calendar business logic. Matches
    // QtQuick MonthGrid's own rendering exactly (verified: both derive the
    // grid start from Qt.locale().firstDayOfWeek the same way).
    function _computeGridRange(year, month) {
        const firstOfMonth = new Date(year, month, 1)
        const firstDow = Qt.locale().firstDayOfWeek
        const offset = (firstOfMonth.getDay() - firstDow + 7) % 7
        const start = new Date(year, month, 1 - offset)
        const end = new Date(start)
        end.setDate(start.getDate() + 41)
        return { start: start, end: end }
    }

    function _refreshMonth() {
        if (!root.workspaceController || root.calendarId.length === 0 || root._year === 0) {
            return
        }
        const range = root._computeGridRange(root._year, root._month)
        const startIso = root._isoDate(range.start)
        const endIso = root._isoDate(range.end)
        root._loading = true
        const result = root.workspaceController.calendarMonthRange(root.calendarId, startIso, endIso)
        root._loading = false
        if (!result || result.ok !== true) {
            root._errorMessage = (result && result.errorMessage) || "Unable to load calendar data for this month."
            return
        }
        root._errorMessage = ""
        const byDate = {}
        const days = result.days || []
        for (let i = 0; i < days.length; i += 1) {
            byDate[days[i].date] = days[i]
        }
        root._daysByDate = byDate
    }

    function _goToMonthContaining(dateIso) {
        const parts = dateIso.split("-")
        root._year = parseInt(parts[0], 10)
        root._month = parseInt(parts[1], 10) - 1
        root._refreshMonth()
    }

    function _initializeToBusinessToday() {
        if (!root.workspaceController || root.calendarId.length === 0 || root._initialized) {
            return
        }
        root._initialized = true
        root._businessToday = root.workspaceController.calendarBusinessToday(root.calendarId) || ""
        if (root._businessToday.length > 0) {
            root._selectedDate = root._businessToday
            root._goToMonthContaining(root._businessToday)
        }
    }

    onCalendarIdChanged: root._initializeToBusinessToday()
    Component.onCompleted: root._initializeToBusinessToday()

    ColumnLayout {
        id: _layout
        width: parent ? parent.width : root.width
        spacing: Theme.AppTheme.spacingMd

        CalendarMonth.CalendarMonthToolbar {
            objectName: "calendarMonthToolbar"
            Layout.fillWidth: true
            monthLabel: root._monthLabel
            busy: root._loading
            onPreviousRequested: {
                const prevMonth = root._month === 0 ? 11 : root._month - 1
                const prevYear = root._month === 0 ? root._year - 1 : root._year
                root._year = prevYear
                root._month = prevMonth
                root._refreshMonth()
            }
            onNextRequested: {
                const nextMonth = root._month === 11 ? 0 : root._month + 1
                const nextYear = root._month === 11 ? root._year + 1 : root._year
                root._year = nextYear
                root._month = nextMonth
                root._refreshMonth()
            }
            onTodayRequested: {
                root._businessToday = root.workspaceController
                    ? (root.workspaceController.calendarBusinessToday(root.calendarId) || root._businessToday)
                    : root._businessToday
                if (root._businessToday.length > 0) {
                    root._selectedDate = root._businessToday
                    root._goToMonthContaining(root._businessToday)
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._errorMessage.length > 0
            tone: "danger"
            message: root._errorMessage

            AppControls.SecondaryButton {
                text: "Retry"
                onClicked: root._refreshMonth()
            }
        }

        RowLayout {
            id: _calendarRow
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            // The grid area owns its own scrolling in both directions --
            // it never shrinks cells below a readable minimum width, and
            // never grows the whole view's height past a bounded amount;
            // overflow in either direction pans within this area instead of
            // squeezing content or pushing the page's own scroll around.
            Flickable {
                id: _calendarScroll
                Layout.fillWidth: true
                Layout.preferredHeight: _calendarContent.height
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: _calendarContent.width
                contentHeight: _calendarContent.height

                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                    id: _calendarContent
                    width: Math.max(_calendarScroll.width, 7 * 120)
                    height: implicitHeight
                    spacing: Theme.AppTheme.spacingXs

                    DayOfWeekRow {
                        id: _dayOfWeekRow
                        Layout.fillWidth: true
                        locale: Qt.locale()

                        // The default QtQuick Controls delegate reads the
                        // active style's palette, which does not reliably
                        // track this app's own dark/light theme tokens --
                        // without this override the weekday header can end
                        // up unreadable (e.g. dark text in dark mode).
                        delegate: Text {
                            required property var model
                            text: model.shortName
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.weight: Theme.AppTheme.weightSemibold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    MonthGrid {
                        id: _grid
                        objectName: "calendarMonthGrid"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 6 * 86
                        month: root._month
                        year: root._year
                        locale: Qt.locale()
                        spacing: 0

                        delegate: CalendarMonth.PlatformCalendarDayCell {
                            required property var model

                            readonly property string _dateIso: root._isoDate(model.date)

                            dayData: root._daysByDate[_dateIso] || root._emptyDayData(_dateIso)
                            isCurrentMonth: model.month === _grid.month
                            isSelected: _dateIso === root._selectedDate

                            onActivated: {
                                root._selectedDate = _dateIso
                            }
                        }
                    }
                }
            }

            // Side-by-side with the grid, exactly like every other Detail
            // page's Inspector -- hidden only below the shared compact
            // window-width breakpoint, never reflowed underneath its list.
            AppWidgets.InspectorPanel {
                id: _inspector
                objectName: "calendarDayInspector"
                visible: root._showInspector && Window.width >= Theme.AppTheme.compactContentBreakpoint
                Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: _calendarContent.height

                preferredWidth: 260
                minimumWidth: 190
                availableWidth: root._showInspector ? Math.round(_calendarRow.width * 0.3) : -1

                title: root._inspectorTitle(root._selectedDayData)
                statusLabel: root._inspectorStatusLabel(root._selectedDayData)
                statusTone: root._inspectorStatusTone(root._selectedDayData)
                groups: root._inspectorGroups(root._selectedDayData)

                showEditAction: false
                showSecondaryAction: false
                showViewDetailsAction: false

                onCloseRequested: root._selectedDate = ""

                AppControls.PrimaryButton {
                    Layout.fillWidth: true
                    visible: root.canWrite
                    text: "Add Exception"
                    iconName: "add"
                    onClicked: root.addExceptionRequested(root._selectedDate)
                }
            }
        }
    }
}
