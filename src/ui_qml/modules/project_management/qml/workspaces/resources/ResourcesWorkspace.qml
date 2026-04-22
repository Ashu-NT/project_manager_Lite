import QtQuick
import QtQuick.Layouts
import "../../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../../shared/qml/theme" as Theme
import "../../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Resources"
    subtitle: "QML landing zone for resource capacity, allocation, project assignments, and utilization views."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: "Resources"
            supportingText: "Resource UI state will be exposed through PM view models."
        }
    }
}
