pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.calendars.sections.views 1.0 as CalendarViews

// Calendar Detail's "Calendar" tab: one top-level tab hosting three views
// (Month / Exceptions / Recurring) behind an in-tab switcher, never three
// separate top-level tabs -- see CalendarMonthView.qml for the planned
// Month-view replacement of the first view; Exceptions/Recurring are each
// their own file under sections/views/ so that swap touches nothing else.
Column {
    id: root
    spacing: Theme.AppTheme.spacingMd

    property var exceptions: []
    property var recurringEvents: []
    property string selectedExceptionId: ""
    property string selectedRecurringEventId: ""
    property bool canWrite: true
    property int activeViewIndex: 0

    signal addExceptionRequested()
    signal deleteExceptionRequested()
    signal addRecurringEventRequested()
    signal deleteRecurringEventRequested()
    signal exceptionSelected(string exceptionId)
    signal recurringEventSelected(string eventId)

    readonly property var _viewTabs: [
        "Month",
        { "label": "Exceptions", "count": root.exceptions.length },
        { "label": "Recurring", "count": root.recurringEvents.length }
    ]

    AppWidgets.DetailTabBar {
        width: parent ? parent.width : root.width
        tabs: root._viewTabs
        currentIndex: root.activeViewIndex
        onTabSelected: function(index) { root.activeViewIndex = index }
    }

    CalendarViews.CalendarMonthView {
        width: parent ? parent.width : root.width
        visible: root.activeViewIndex === 0
    }

    CalendarViews.CalendarExceptionsView {
        width: parent ? parent.width : root.width
        visible: root.activeViewIndex === 1
        exceptions: root.exceptions
        selectedExceptionId: root.selectedExceptionId
        canWrite: root.canWrite

        onAddExceptionRequested: root.addExceptionRequested()
        onDeleteExceptionRequested: root.deleteExceptionRequested()
        onExceptionSelected: function(id) { root.exceptionSelected(id) }
    }

    CalendarViews.CalendarRecurringView {
        width: parent ? parent.width : root.width
        visible: root.activeViewIndex === 2
        recurringEvents: root.recurringEvents
        selectedRecurringEventId: root.selectedRecurringEventId
        canWrite: root.canWrite

        onAddRecurringEventRequested: root.addRecurringEventRequested()
        onDeleteRecurringEventRequested: root.deleteRecurringEventRequested()
        onRecurringEventSelected: function(id) { root.recurringEventSelected(id) }
    }
}
