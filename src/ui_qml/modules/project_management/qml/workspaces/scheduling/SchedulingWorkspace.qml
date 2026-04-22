import QtQuick
import QtQuick.Layouts
import "../../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../../shared/qml/theme" as Theme
import "../../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Scheduling"
    subtitle: "QML landing zone for calendars, baseline comparison, dependency graphs, and critical-path views."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: "Scheduling"
            supportingText: "Scheduling engine behavior stays in PM domain/application layers."
        }
    }
}
