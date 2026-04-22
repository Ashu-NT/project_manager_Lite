import QtQuick
import QtQuick.Layouts
import "../../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../../shared/qml/theme" as Theme
import "../../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Risk"
    subtitle: "QML landing zone for project risk register, mitigation, severity, and review workflows."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: "Risk"
            supportingText: "Risk register behavior remains in PM application/domain code."
        }
    }
}
