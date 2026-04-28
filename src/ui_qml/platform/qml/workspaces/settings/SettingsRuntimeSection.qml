import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

RowLayout {
    id: root

    property string themeMode: "light"
    property string platformStatusLabel: ""
    property string workspaceSummary: ""

    spacing: Theme.AppTheme.spacingMd

    AppWidgets.MetricCard {
        Layout.preferredWidth: 240
        label: "Theme"
        value: root.themeMode
        supportingText: "Theme state is exposed through shell runtime bindings."
    }

    AppWidgets.MetricCard {
        Layout.preferredWidth: 240
        label: "Platform API"
        value: root.platformStatusLabel
        supportingText: root.workspaceSummary
    }
}
