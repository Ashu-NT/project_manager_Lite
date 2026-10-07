pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Interim content ahead of the planned Month view (the central
// modernization work -- MonthGrid/DayOfWeekRow wrapped in TECHASH
// components, backed by one bounded resolveCalendarRange() call). Replacing
// this file's contents is the entire scope of that next phase; Exceptions
// and Recurring views are unaffected by it.
Item {
    id: root
    implicitHeight: content.implicitHeight

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            tone: "info"
            message: "A visual month calendar is coming soon. Use the Exceptions and Recurring views to manage this calendar's schedule for now."
        }
    }
}
