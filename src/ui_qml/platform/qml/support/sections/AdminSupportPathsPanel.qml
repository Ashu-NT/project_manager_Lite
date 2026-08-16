pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

ColumnLayout {
    id: root

    property var supportSettings: ({})
    property var supportPaths:    ({})
    property var bundleState:     ({})

    signal openLogsRequested()
    signal openDataRequested()

    Layout.fillWidth: true
    spacing: 0

    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Runtime Paths" }

    SupportPathRow {
        rowLabel: "Support Contact"
        rowValue: String(root.supportSettings.supportEmail || root.bundleState.supportEmail || "")
        canOpen:  false
    }
    SupportPathRow {
        rowLabel: "Logs"; rowValue: String(root.supportPaths.logsDirectoryPath || "")
        canOpen:  true; onOpenRequested: root.openLogsRequested()
    }
    SupportPathRow {
        rowLabel: "Data"; rowValue: String(root.supportPaths.dataDirectoryPath || "")
        canOpen:  true; onOpenRequested: root.openDataRequested()
    }
}
