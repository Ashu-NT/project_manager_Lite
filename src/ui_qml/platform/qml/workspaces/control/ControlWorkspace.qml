import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "Control Center"
    subtitle: "QML landing zone for approvals, audit review, runtime visibility, and operational control workflows."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Migration target"
            value: "Control"
            supportingText: "Presenter and view-model wiring will be added per migrated workflow."
        }

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Runtime"
            value: "Safe"
            supportingText: "The current QWidget control screens remain the active implementation."
        }
    }
}
