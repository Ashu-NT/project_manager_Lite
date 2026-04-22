import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Settings"
    subtitle: "QML landing zone for shell preferences, theme controls, governance mode, and desktop runtime settings."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Migration target"
            value: "Settings"
            supportingText: "This will replace Widget settings only after QML state persistence is verified."
        }

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Theme"
            value: shellContext.themeMode
            supportingText: "Theme state is exposed through shellContext for QML binding."
        }
    }
}
