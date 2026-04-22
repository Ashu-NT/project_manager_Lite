import QtQuick
import QtQuick.Layouts
import "../../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../../shared/qml/theme" as Theme
import "../../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Financials"
    subtitle: "QML landing zone for project cost, labor, baseline budget, and financial reporting workflows."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: "Financials"
            supportingText: "Cost and finance UI maps to the PM financials subdomain."
        }
    }
}
