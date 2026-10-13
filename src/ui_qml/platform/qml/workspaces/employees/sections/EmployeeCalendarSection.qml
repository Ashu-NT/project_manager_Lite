pragma ComponentBehavior: Bound
import QtQuick
import workspaces.calendars 1.0

// Employee Detail's Calendar tab -- the shared, generic calendar-assignment
// section also used by Site/Department Detail (see
// AdminCalendarAssignmentSection). An Employee calendar is always an
// optional override, resolved through the real chain (Employee override,
// else Department, else Site, else the Organization default); this
// component never creates a mandatory standalone Employee calendar, and
// calendar configuration/editing stays exclusively in Platform > Calendars.
AdminCalendarAssignmentSection {
    id: root
    width: parent ? parent.width : 0
    entityType: "employee"
    // The Effective Calendar card already carries the necessary
    // information (name, source, rules) plus an "Open Calendar" action in
    // this tab's own section toolbar -- an unconditional banner and a
    // second card devoted to explaining Calendar Management would be
    // redundant here.
    showGuidanceCard: false
}
