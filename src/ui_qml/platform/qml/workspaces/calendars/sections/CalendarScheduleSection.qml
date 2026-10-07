pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import workspaces.calendars.sections.views 1.0 as CalendarViews

// Calendar Detail's "Calendar" tab: one top-level tab hosting three views
// (Month / Exceptions / Recurring) behind an in-tab switcher, never three
// separate top-level tabs. The switcher itself (a DetailTabBar) lives in
// AdminCalendarDetailPage.qml as pinned (detailPagePinned) content, not
// here -- that keeps it visible while this section's own content scrolls,
// and makes activeViewIndex purely an inbound prop from the parent (no
// internal tab bar here writing back to it, which would otherwise sever
// that binding the moment the view switches -- see
// AdminCalendarDetailPage.qml's onCalendarActiveViewIndexChanged for the
// selection-clearing this used to also do locally).
Column {
    id: root
    objectName: "calendarScheduleSection"
    spacing: Theme.AppTheme.spacingMd

    property string calendarId: ""
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property var exceptions: []
    property var recurringEvents: []
    property var workingRules: []
    property string selectedExceptionId: ""
    property string selectedRecurringEventId: ""
    property bool canWrite: true
    property int activeViewIndex: 0

    signal addExceptionRequested()
    signal addExceptionForDateRequested(string date)
    signal editExceptionRequested(string exceptionId)
    signal deleteExceptionRequested()
    signal addRecurringEventRequested()
    signal editRecurringEventRequested(string eventId)
    signal deleteRecurringEventRequested()
    signal toggleRecurringEventActiveRequested(string eventId, bool active)
    signal exceptionSelected(string exceptionId)
    signal recurringEventSelected(string eventId)

    // One fixed content-area height shared by all three views -- switching
    // between Month (always 6 grid rows) and Exceptions/Recurring (whose
    // row count varies) must never resize this tab or make the page jump;
    // each view scrolls internally within this fixed area instead.
    readonly property int _fixedContentHeight: 560

    CalendarViews.CalendarMonthView {
        width: parent ? parent.width : root.width
        visible: root.activeViewIndex === 0
        workspaceController: root.workspaceController
        calendarId: root.calendarId
        canWrite: root.canWrite
        fixedContentHeight: root._fixedContentHeight

        onAddExceptionRequested: function(date) { root.addExceptionForDateRequested(date) }
    }

    CalendarViews.CalendarExceptionsView {
        width: parent ? parent.width : root.width
        visible: root.activeViewIndex === 1
        workspaceController: root.workspaceController
        calendarId: root.calendarId
        exceptions: root.exceptions
        workingRules: root.workingRules
        selectedExceptionId: root.selectedExceptionId
        canWrite: root.canWrite
        fixedContentHeight: root._fixedContentHeight

        onAddExceptionRequested: root.addExceptionRequested()
        onEditExceptionRequested: function(id) { root.editExceptionRequested(id) }
        onDeleteExceptionRequested: root.deleteExceptionRequested()
        onExceptionSelected: function(id) { root.exceptionSelected(id) }
    }

    CalendarViews.CalendarRecurringView {
        width: parent ? parent.width : root.width
        visible: root.activeViewIndex === 2
        recurringEvents: root.recurringEvents
        selectedRecurringEventId: root.selectedRecurringEventId
        canWrite: root.canWrite
        fixedContentHeight: root._fixedContentHeight

        onAddRecurringEventRequested: root.addRecurringEventRequested()
        onEditRecurringEventRequested: function(id) { root.editRecurringEventRequested(id) }
        onDeleteRecurringEventRequested: root.deleteRecurringEventRequested()
        onToggleActiveRequested: function(id, active) { root.toggleRecurringEventActiveRequested(id, active) }
        onRecurringEventSelected: function(id) { root.recurringEventSelected(id) }
    }
}
