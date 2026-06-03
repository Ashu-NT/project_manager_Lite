pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import "../components"

Item {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property var calendar: ({})
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0
    property string selectedHolidayId: ""
    property string selectedRuleId: ""
    property string selectedExceptionId: ""
    property string selectedRecurringEventId: ""
    property string calculationStartDate: ""
    property string calculationWorkingDays: ""
    property string calculationResult: ""
    property var workingRules: []
    property var enterpriseExceptions: []
    property var recurringEvents: []
    property var assignments: ({})
    property bool isEnterpriseCalendar: false

    signal backRequested()
    signal editRequested()
    signal addHolidayRequested()
    signal addExceptionRequested()
    signal addRecurringEventRequested()
    signal openAuditRequested()

    readonly property var _state: (root.calendar && root.calendar.state) ? root.calendar.state : ({})
    readonly property string _title: String(root.calendar && root.calendar.title ? root.calendar.title : "Working Calendar")
    readonly property string _workingDaysText: String(root._state.workingDaysText || "No working days configured")
    readonly property string _hoursPerDayLabel: String(root._state.hoursPerDayLabel || root._state.hoursPerDay || "8")
    readonly property var _holidayRows: root._state.holidays || []
    readonly property var _sections: {
        const base = [
            { "label": "Overview" },
            { "label": "Holidays", "count": root._holidayRows.length }
        ]
        if (root.isEnterpriseCalendar) {
            base.push({ "label": "Working Rules", "count": root.workingRules.length })
            base.push({ "label": "Exceptions", "count": root.enterpriseExceptions.length })
            base.push({ "label": "Recurring Events", "count": root.recurringEvents.length })
            base.push({ "label": "Assignments" })
        }
        base.push({ "label": "Calculator" })
        base.push({ "label": "Audit" })
        return base
    }
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "edit", "label": "Edit Calendar", "icon": "edit" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Holidays") {
            return [
                { "id": "add_holiday", "label": "Add Exception", "icon": "add" },
                { "id": "delete_holiday", "label": "Delete Exception", "icon": "delete", "danger": true, "enabled": root.selectedHolidayId.length > 0 },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Exceptions") {
            return [
                { "id": "add_exception", "label": "Add Exception", "icon": "add" },
                { "id": "delete_exception", "label": "Delete", "icon": "delete", "danger": true, "enabled": root.selectedExceptionId.length > 0 },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Recurring Events") {
            return [
                { "id": "add_recurring", "label": "Add Recurring Event", "icon": "add" },
                { "id": "delete_recurring", "label": "Delete", "icon": "delete", "danger": true, "enabled": root.selectedRecurringEventId.length > 0 },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Working Rules") {
            return [
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Assignments") {
            return [
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Calculator") {
            return [
                { "id": "calculate", "label": "Calculate Days", "icon": "refresh" }
            ]
        }
        return [
            { "id": "open_audit", "label": "Open Audit", "icon": "history" }
        ]
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":
            return "Shared working-week rules owned by Platform and consumed by PM Scheduling and other modules."
        case "Holidays":
            return "Holiday and non-working-day exceptions for the shared working calendar."
        case "Working Rules":
            return "Weekday working schedule — start/end times, breaks, and hours per day."
        case "Exceptions":
            return "Date-specific exceptions: holidays, shutdowns, overtime, and availability overrides."
        case "Recurring Events":
            return "Recurring meetings, training, maintenance windows, and on-call blocks that affect capacity."
        case "Assignments":
            return "Sites, departments, employees, projects, and resources assigned to this calendar."
        case "Calculator":
            return "Preview working-day finish dates using the current shared calendar."
        case "Audit":
            return "Calendar governance stays in the shared platform audit and approval flow."
        default:
            return ""
        }
    }
    readonly property var _holidayColumns: [
        { "key": "date", "label": "Date", "flex": 1.0, "sortable": true },
        { "key": "name", "label": "Exception", "flex": 1.8 },
        { "key": "calendar", "label": "Calendar", "flex": 1.4 },
        { "key": "details", "label": "Details", "flex": 1.8 }
    ]
    readonly property var _workingRuleColumns: [
        { "key": "weekday", "label": "Day", "flex": 0.8 },
        { "key": "isWorkingDay", "label": "Working", "flex": 0.7 },
        { "key": "startTime", "label": "Start", "flex": 0.8 },
        { "key": "endTime", "label": "End", "flex": 0.8 },
        { "key": "breakMinutes", "label": "Break (min)", "flex": 0.8 },
        { "key": "computedHours", "label": "Hours", "flex": 0.7 }
    ]
    readonly property var _exceptionColumns: [
        { "key": "exceptionDate", "label": "Date", "flex": 0.9 },
        { "key": "exceptionType", "label": "Type", "flex": 1.0 },
        { "key": "name", "label": "Name", "flex": 1.4 },
        { "key": "impactType", "label": "Impact", "flex": 1.0 },
        { "key": "approvalStatus", "label": "Status", "flex": 0.8 }
    ]
    readonly property var _recurringColumns: [
        { "key": "title", "label": "Title", "flex": 1.4 },
        { "key": "eventType", "label": "Type", "flex": 0.9 },
        { "key": "recurrenceRule", "label": "Recurrence", "flex": 1.6 },
        { "key": "impactType", "label": "Impact", "flex": 0.9 },
        { "key": "isActive", "label": "Active", "flex": 0.6 }
    ]
    readonly property var _overviewFields: [
        { "label": "Calendar Name", "value": root._title },
        { "label": "Ownership", "value": root.isEnterpriseCalendar ? "Enterprise Calendar" : "Platform Shared Master" },
        { "label": "Hours / Day", "value": root._hoursPerDayLabel + "h" },
        { "label": "Working Days", "value": root._workingDaysText },
        { "label": "Exceptions", "value": String(root._holidayRows.length) },
        { "label": "Calendar ID", "value": root._state.calendarId || "default" }
    ]

    function _tableHeightForCount(count) {
        const visibleRows = Math.max(1, Math.min(count, 8))
        return Theme.AppTheme.headerHeight + (visibleRows * Theme.AppTheme.normalRowHeight) + Theme.AppTheme.spacingLg
    }

    function _runCalculation() {
        if (root.workspaceController === null)
            return
        const result = root.workspaceController.calculateCalendarWorkingDays({
            "startDate": root.calculationStartDate,
            "workingDays": root.calculationWorkingDays
        })
        if (result && result.ok === true) {
            root.calculationResult = String(result.message || "")
        } else {
            root.calculationResult = ""
        }
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        isBusy: root.busy
        showEdit: false
        showDelete: false
        sections: root._sections

        onBackRequested: root.backRequested()
        onSectionChanged: function(index) {
            root.activeSectionIndex = index
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                if (actionId === "edit") {
                    root.editRequested()
                } else if (actionId === "add_holiday") {
                    root.addHolidayRequested()
                } else if (actionId === "add_exception") {
                    root.addExceptionRequested()
                } else if (actionId === "add_recurring") {
                    root.addRecurringEventRequested()
                } else if (actionId === "delete_holiday") {
                    if (root.workspaceController !== null && root.selectedHolidayId.length > 0) {
                        const result = root.workspaceController.deleteCalendarHoliday(root.selectedHolidayId)
                        if (result && result.ok === true)
                            root.selectedHolidayId = ""
                    }
                } else if (actionId === "delete_exception") {
                    if (root.workspaceController !== null && root.selectedExceptionId.length > 0) {
                        const result = root.workspaceController.deleteCalendarException(root.selectedExceptionId)
                        if (result && result.ok === true)
                            root.selectedExceptionId = ""
                    }
                } else if (actionId === "delete_recurring") {
                    if (root.workspaceController !== null && root.selectedRecurringEventId.length > 0) {
                        const result = root.workspaceController.deleteCalendarRecurringEvent(root.selectedRecurringEventId)
                        if (result && result.ok === true)
                            root.selectedRecurringEventId = ""
                    }
                } else if (actionId === "refresh") {
                    if (root.workspaceController !== null)
                        root.workspaceController.refresh()
                } else if (actionId === "calculate") {
                    root._runCalculation()
                } else if (actionId === "open_audit") {
                    root.openAuditRequested()
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading calendar overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Overview"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: overviewColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: overviewColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: "This shared calendar is managed in Platform Admin and consumed read-only by PM scheduling workspaces."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Calendar Summary"
                                    outlined: true

                                    GridLayout {
                                        id: overviewGrid
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        columns: 2
                                        columnSpacing: Theme.AppTheme.spacingLg
                                        rowSpacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._overviewFields

                                            delegate: ColumnLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: 2

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: modelData.value === undefined || modelData.value === null || String(modelData.value).length === 0
                                                        ? "-"
                                                        : String(modelData.value)
                                                    color: Theme.AppTheme.textPrimary
                                                    font.pixelSize: Theme.AppTheme.smallSize
                                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Holidays" ? holidaysLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: holidaysLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Holidays"
                keepLoaded: true
                loadingMessage: "Loading calendar exceptions..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Holiday Exceptions"
                        infoMessage: "These exceptions are shared across any module that consumes the Platform working calendar."
                        rows: root._holidayRows
                        columns: root._holidayColumns
                        selectedRowId: root.selectedHolidayId
                        emptyTitle: "No exceptions yet"
                        emptyMessage: "No holiday or non-working-day exceptions are configured."
                        tableHeight: root._tableHeightForCount(root._holidayRows.length)
                        onRowSelected: function(rowId) {
                            root.selectedHolidayId = String(rowId || "")
                        }
                        onRowActivated: function(rowId) {
                            root.selectedHolidayId = String(rowId || "")
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Working Rules" ? workingRulesLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: workingRulesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Working Rules"
                keepLoaded: true
                loadingMessage: "Loading working rules..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Working Rules"
                        infoMessage: "Weekday working schedule for this calendar. Each row defines one day's start/end time and break."
                        rows: root.workingRules
                        columns: root._workingRuleColumns
                        emptyTitle: "No working rules defined"
                        emptyMessage: "Use the working rule editor to define the working week schedule."
                        tableHeight: root._tableHeightForCount(7)
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Exceptions" ? enterpriseExceptionsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: enterpriseExceptionsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Exceptions"
                keepLoaded: true
                loadingMessage: "Loading exceptions..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Exceptions"
                        infoMessage: "Date-specific exceptions override working rules. Holidays, shutdowns, overtime, and reduced-hours events are defined here."
                        rows: root.enterpriseExceptions
                        columns: root._exceptionColumns
                        selectedRowId: root.selectedExceptionId
                        emptyTitle: "No exceptions defined"
                        emptyMessage: "Add exceptions for holidays, shutdowns, or other non-standard days."
                        tableHeight: root._tableHeightForCount(root.enterpriseExceptions.length)
                        onRowSelected: function(rowId) { root.selectedExceptionId = String(rowId || "") }
                        onRowActivated: function(rowId) { root.selectedExceptionId = String(rowId || "") }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Recurring Events" ? recurringEventsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: recurringEventsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Recurring Events"
                keepLoaded: true
                loadingMessage: "Loading recurring events..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Recurring Events"
                        infoMessage: "Recurring meetings, training, and maintenance windows that reduce available capacity on a schedule."
                        rows: root.recurringEvents
                        columns: root._recurringColumns
                        selectedRowId: root.selectedRecurringEventId
                        emptyTitle: "No recurring events"
                        emptyMessage: "Add recurring events that regularly reduce available working capacity."
                        tableHeight: root._tableHeightForCount(root.recurringEvents.length)
                        onRowSelected: function(rowId) { root.selectedRecurringEventId = String(rowId || "") }
                        onRowActivated: function(rowId) { root.selectedRecurringEventId = String(rowId || "") }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Assignments" ? assignmentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: assignmentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Assignments"
                keepLoaded: true
                loadingMessage: "Loading calendar assignments..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Assignments"
                        infoMessage: "This calendar is assigned to the following sites, departments, employees, projects, and resources."
                        cardTitle: "Usage"
                        notes: {
                            const lines = []
                            const a = root.assignments || {}
                            const sites = (a.sites || []).length
                            const depts = (a.departments || []).length
                            const emps = (a.employees || []).length
                            const projs = (a.projects || []).length
                            const ress = (a.resources || []).length
                            if (sites > 0) lines.push("Sites: " + sites + " assignment(s)")
                            if (depts > 0) lines.push("Departments: " + depts + " assignment(s)")
                            if (emps > 0) lines.push("Employees: " + emps + " assignment(s)")
                            if (projs > 0) lines.push("Projects: " + projs + " assignment(s)")
                            if (ress > 0) lines.push("Resources: " + ress + " assignment(s)")
                            if (lines.length === 0) lines.push("No active assignments. Assign this calendar from Site, Department, Employee, Project, or Resource detail pages.")
                            return lines
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Calculator" ? calculatorLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: calculatorLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Calculator"
                keepLoaded: true
                loadingMessage: "Loading calendar calculator..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Calculator"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: calculatorColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: calculatorColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: calculatorForm.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Working-Day Preview"
                                    outlined: true

                                    ColumnLayout {
                                        id: calculatorForm
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingMd

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: "Preview finish dates using the shared Platform working calendar."
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: Theme.AppTheme.spacingMd

                                            AppWidgets.FormField {
                                                Layout.fillWidth: true
                                                label: "Start Date"

                                                AppControls.DateField {
                                                    id: calcStartField
                                                    Layout.fillWidth: true
                                                    placeholderText: "YYYY-MM-DD"
                                                    text: root.calculationStartDate
                                                    onTextChanged: {
                                                        if (root.calculationStartDate !== text)
                                                            root.calculationStartDate = text
                                                    }
                                                }
                                            }

                                            AppWidgets.FormField {
                                                Layout.preferredWidth: 140
                                                label: "Working Days"

                                                AppControls.TextField {
                                                    id: calcDaysField
                                                    Layout.fillWidth: true
                                                    placeholderText: "e.g. 5"
                                                    text: root.calculationWorkingDays
                                                    onTextChanged: {
                                                        if (root.calculationWorkingDays !== text)
                                                            root.calculationWorkingDays = text
                                                    }
                                                }
                                            }
                                        }

                                        AppWidgets.InlineMessage {
                                            Layout.fillWidth: true
                                            visible: root.calculationResult.length > 0
                                            tone: "success"
                                            message: root.calculationResult
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Audit" ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Audit"
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Shared calendar changes participate in platform governance and can affect PM scheduling calculations."
                        cardTitle: "Audit & Ownership"
                        notes: [
                            "Platform owns shared working-calendar rules, holiday exceptions, and working-day calculations.",
                            "Project Management consumes this calendar for schedule logic and preview calculations, but does not own the CRUD workflow.",
                            "Use the shared audit workspace to review change history and operational follow-up."
                        ]
                    }
                }
            }
        }
    }
}
