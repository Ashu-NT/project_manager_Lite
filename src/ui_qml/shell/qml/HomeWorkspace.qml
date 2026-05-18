import QtQuick
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    id: root
    property ShellContexts.ShellContext shellModel

    title: "Home"
    subtitle: "Select a workspace from the navigation to get started."

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.MetricCard {
                Layout.preferredWidth: 220
                label: "Workspaces"
                value: root.shellModel ? root.shellModel.navigationItems.length + "" : "0"
                supportingText: "Registered navigable workspaces."
            }
        }
    }
}
