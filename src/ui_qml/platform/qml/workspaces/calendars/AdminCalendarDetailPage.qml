pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import workspaces.calendars.sections 1.0 as CalendarSections

// Orchestrator only: owns calendar identity/lifecycle, per-tab state, and
// data fetching -- each tab's own markup lives in workspaces/calendars/
// sections/ (see that folder for Overview/Schedule/Assignments/Activity).
// "Schedule" is the interim content for the target "Calendar" tab ahead of
// the planned visual Month view (see CalendarScheduleSection.qml).
Item {
    id: root
    objectName: "adminCalendarDetailPage"

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property var calendar: ({})
    property var breadcrumb: []
    property bool canWrite: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0
    property string selectedExceptionId: ""
    property string selectedRecurringEventId: ""

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _state: (root.calendar && root.calendar.state) ? root.calendar.state : ({})
    readonly property string _title: String(root.calendar && root.calendar.title ? root.calendar.title : "Calendar")
    readonly property string _calendarId: String(root._state.calendarId || root._state.id || root.calendar.id || "")
    readonly property string _organizationId: String(root._state.organizationId || "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property bool _isDefault: root._state.isDefault === true
    readonly property string _headerSubtitle: root._joinNonEmpty(
        [String(root._state.code || ""), String(root._state.timeZone || "")], "  ·  "
    )

    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "-"
    }

    // Reflects backend capability state (isDefault) rather than re-deriving
    // the Organization-default protection rule in QML -- the backend
    // independently enforces CALENDAR_DEFAULT_CANNOT_DEACTIVATE/
    // CALENDAR_DEFAULT_CANNOT_DELETE regardless of what this menu offers.
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit calendar", "icon": "edit", "enabled": root.canWrite },
            { "separator": true }
        ]
        if (root._isActive) {
            if (!root._isDefault) {
                items.push({ "id": "deactivate", "label": "Deactivate calendar", "icon": "reject", "enabled": root.canWrite })
            }
        } else {
            items.push({ "id": "activate", "label": "Activate calendar", "icon": "approve", "enabled": root.canWrite })
        }
        if (!root._isDefault) {
            items.push({ "id": "delete", "label": "Delete calendar", "icon": "delete", "danger": true, "enabled": root.canWrite })
        }
        return items
    }

    property var _overview: ({
        "workingRules": [], "exceptions": [], "recurringEvents": [],
        "assignments": { "sites": [], "departments": [], "employees": [], "projects": [], "resources": [] },
        "usage": { "isOrganizationDefault": false, "sites": 0, "departments": 0, "employees": 0, "projects": 0, "resources": 0 },
        "upcomingExceptions": [], "shiftPatternLabel": "", "recentActivity": []
    })
    function _refreshOverview() {
        if (root._calendarId.length === 0 || !root.workspaceController) {
            return
        }
        root._overview = root.workspaceController.calendarOverviewContext(root._calendarId)
    }

    property int _activityPage: 1
    property int _activityPageSize: 25
    property string _activitySearch: ""
    property string _activityDateFilter: ""
    property var _activityCatalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    readonly property var _activityDateFilterOptions: [
        { "value": "", "label": "All time" },
        { "value": "today", "label": "Today" },
        { "value": "7d", "label": "Last 7 days" },
        { "value": "30d", "label": "Last 30 days" }
    ]
    function _refreshActivityPage() {
        if (root._calendarId.length === 0 || root._organizationId.length === 0 || !root.workspaceController) {
            return
        }
        root._activityCatalog = root.workspaceController.calendarActivityPage(
            root._calendarId, root._organizationId, root._activityPage, root._activityPageSize,
            root._activitySearch, root._activityDateFilter
        )
    }

    onCalendarChanged: {
        root._refreshOverview()
        root._refreshActivityPage()
    }
    // Exception/recurring-rule mutations are dispatched through the
    // workspace page's shared dialog host (actionRequested("add_exception")
    // etc.), which only refreshes the Calendars workspace catalog on
    // success -- feedbackMessage changing is the one signal this page
    // receives back that a mutation actually completed, so it re-fetches
    // its own overview/activity in response rather than polling.
    onFeedbackMessageChanged: {
        if (root.feedbackMessage.length > 0) {
            root._refreshOverview()
            root._refreshActivityPage()
        }
    }
    Component.onCompleted: {
        root._refreshOverview()
        root._refreshActivityPage()
    }

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Calendar" },
        { "label": "Assignments" },
        { "label": "Activity" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    function _indexOfSection(label) {
        for (let i = 0; i < root._sections.length; i += 1) {
            if (root._sections[i].label === label) return i
        }
        return -1
    }

    readonly property var _calendarInfoFields: [
        { "label": "Calendar Name", "value": root._displayValue(root._state.name || root.calendar.title) },
        { "label": "Calendar Code", "value": root._displayValue(root._state.code) },
        { "label": "Time Zone", "value": root._displayValue(root._state.timeZone) },
        { "label": "Type", "value": root._displayValue(root._state.typeLabel) },
        { "label": "Description", "value": root._displayValue(root._state.description) },
        { "label": "Effective From", "value": root._displayValue(root._state.effectiveFrom) },
        { "label": "Effective To", "value": root._displayValue(root._state.effectiveTo) }
    ]

    property var _pendingConfirm: null

    function _requestDeleteExceptionConfirm() {
        if (root.selectedExceptionId.length === 0) return
        const exc = (root._overview.exceptions || []).find(function(e) { return String(e.id) === root.selectedExceptionId })
        const name = exc ? String(exc.name || "this exception") : "this exception"
        root._pendingConfirm = {
            "type": "delete_exception",
            "message": "Delete " + name + "?",
            "supportingText": "This calendar exception will be permanently removed."
        }
        confirmDialog.open()
    }
    function _requestDeleteRecurringEventConfirm() {
        if (root.selectedRecurringEventId.length === 0) return
        const event = (root._overview.recurringEvents || []).find(function(e) { return String(e.id) === root.selectedRecurringEventId })
        const title = event ? String(event.title || "this recurring rule") : "this recurring rule"
        root._pendingConfirm = {
            "type": "delete_recurring",
            "message": "Delete " + title + "?",
            "supportingText": "This recurring rule will be permanently removed."
        }
        confirmDialog.open()
    }

    function _navigateFromOverview(destinationId) {
        const label = destinationId === "assignments" ? "Assignments"
            : destinationId === "activity" ? "Activity"
            : destinationId === "calendar" ? "Calendar"
            : ""
        const index = label.length > 0 ? root._indexOfSection(label) : -1
        if (index >= 0) {
            detailPage.scrollToSection(index)
            return
        }
        root.actionRequested(destinationId)
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        statusLabel: root._isActive ? "Active" : "Inactive"
        statusTone: root._isActive ? "success" : "neutral"
        subtitleLine: root._headerSubtitle
        breadcrumb: root.breadcrumb
        isBusy: root.busy
        showEdit: root.canWrite
        showDelete: false
        menuActions: root.canWrite ? root._lifecycleMenuItems : []
        sections: root._sections

        onBackRequested: root.backRequested()
        onEditRequested: root.actionRequested("edit")
        onMenuActionTriggered: function(id) { root.actionRequested(id) }
        onSectionChanged: function(index) {
            root.activeSectionIndex = index
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
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
                    CalendarSections.CalendarOverviewSection {
                        calendarInfoFields: root._calendarInfoFields
                        workingRules: root._overview.workingRules || []
                        exceptionsCount: (root._overview.exceptions || []).length
                        recurringRulesCount: (root._overview.recurringEvents || []).length
                        shiftPatternLabel: String(root._overview.shiftPatternLabel || "")
                        usage: root._overview.usage
                        upcomingExceptions: root._overview.upcomingExceptions || []
                        recentActivity: root._overview.recentActivity || []

                        onManageExceptionsRequested: {
                            const index = root._indexOfSection("Calendar")
                            if (index >= 0) detailPage.scrollToSection(index)
                        }
                        onManageRecurringRulesRequested: {
                            const index = root._indexOfSection("Calendar")
                            if (index >= 0) detailPage.scrollToSection(index)
                        }
                        onViewAllActivityRequested: {
                            const index = root._indexOfSection("Activity")
                            if (index >= 0) detailPage.scrollToSection(index)
                        }
                        onNavigateToDestination: function(destinationId) {
                            root._navigateFromOverview(destinationId)
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Calendar" ? scheduleLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: scheduleLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Calendar"
                keepLoaded: true
                loadingMessage: "Loading calendar schedule..."
                sourceComponent: Component {
                    CalendarSections.CalendarScheduleSection {
                        width: parent ? parent.width : 0
                        exceptions: root._overview.exceptions || []
                        recurringEvents: root._overview.recurringEvents || []
                        selectedExceptionId: root.selectedExceptionId
                        selectedRecurringEventId: root.selectedRecurringEventId
                        canWrite: root.canWrite

                        onAddExceptionRequested: root.actionRequested("add_exception")
                        onDeleteExceptionRequested: root._requestDeleteExceptionConfirm()
                        onAddRecurringEventRequested: root.actionRequested("add_recurring")
                        onDeleteRecurringEventRequested: root._requestDeleteRecurringEventConfirm()
                        onExceptionSelected: function(id) { root.selectedExceptionId = id }
                        onRecurringEventSelected: function(id) { root.selectedRecurringEventId = id }
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
                    CalendarSections.CalendarAssignmentsSection {
                        height: Math.max(360, detailPage.contentViewportHeight)
                        assignments: root._overview.assignments
                        isOrganizationDefault: root._overview.usage ? !!root._overview.usage.isOrganizationDefault : false
                        busy: root.busy
                        onRefreshRequested: root._refreshOverview()
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Activity"
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: activityLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Activity"
                keepLoaded: true
                loadingMessage: "Loading calendar activity..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    CalendarSections.CalendarActivitySection {
                        width: parent ? parent.width : 0
                        height: Math.max(420, detailPage.contentViewportHeight)
                        catalog: root._activityCatalog
                        busy: root.busy
                        searchText: root._activitySearch
                        dateFilterOptions: root._activityDateFilterOptions
                        dateFilter: root._activityDateFilter

                        onRefreshRequested: root._refreshActivityPage()
                        onSearchChanged: function(text) {
                            root._activitySearch = text
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                        onDateFilterRequested: function(value) {
                            root._activityDateFilter = value
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                        onPageRequested: function(page) {
                            root._activityPage = page
                            root._refreshActivityPage()
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._activityPageSize = pageSize
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                    }
                }
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: confirmDialog
        title: "Confirm"
        confirmLabel: "Delete"
        confirmIcon: "delete"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            if (pending.type === "delete_exception") {
                const result = root.workspaceController.deleteCalendarException(root.selectedExceptionId)
                if (result && result.ok === true) {
                    root.selectedExceptionId = ""
                    root._refreshOverview()
                }
            } else if (pending.type === "delete_recurring") {
                const result = root.workspaceController.deleteCalendarRecurringEvent(root.selectedRecurringEventId)
                if (result && result.ok === true) {
                    root.selectedRecurringEventId = ""
                    root._refreshOverview()
                }
            }
            root._pendingConfirm = null
        }
    }
}
