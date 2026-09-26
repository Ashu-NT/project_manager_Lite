pragma ComponentBehavior: Bound
import QtQuick
import workspaces.calendars 1.0

// Site Detail's Calendar tab -- the shared, generic calendar-assignment
// section also used by Department/Employee Detail (see
// AdminCalendarAssignmentSection). A Site calendar is always an optional
// override of the Organization default calendar; this component never
// creates a mandatory standalone Site calendar, and calendar
// configuration/editing stays exclusively in Platform > Calendars.
AdminCalendarAssignmentSection {
    id: root
    width: parent ? parent.width : 0
    entityType: "site"
}
