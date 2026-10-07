pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
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

        GridLayout {
            Layout.fillWidth: true
            columns: root.width < 900 ? 1 : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: parent.columns === 2 ? Math.round(parent.width * 0.68) : parent.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingXs

                DayOfWeekRow {
                    Layout.fillWidth: true
                    locale: Qt.locale()
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

            CalendarMonth.PlatformCalendarDayDetails {
                objectName: "calendarDayDetails"
                Layout.fillWidth: true
                Layout.preferredWidth: parent.columns === 2
                    ? parent.width - Math.round(parent.width * 0.68) - Theme.AppTheme.spacingMd
                    : parent.width
                Layout.alignment: Qt.AlignTop
                dayData: root._selectedDayData
                canWrite: root.canWrite

                onAddExceptionRequested: function(date) { root.addExceptionRequested(date) }
            }
        }
    }
}
