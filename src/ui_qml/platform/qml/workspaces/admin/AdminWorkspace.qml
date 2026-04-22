import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Admin Console"
    subtitle: "QML landing zone for access, users, organizations, sites, departments, documents, and support administration."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Migration target"
            value: "Admin"
            supportingText: "Existing QWidget admin screens remain active until each replacement is complete."
        }

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Safety rule"
            value: "No delete"
            supportingText: "Legacy widgets are removed only after QML parity and tests."
        }
    }
}
