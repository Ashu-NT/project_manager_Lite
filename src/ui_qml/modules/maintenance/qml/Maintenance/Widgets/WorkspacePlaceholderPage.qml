import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property string routeId: ""
    property string fallbackTitle: ""
    property string fallbackSummary: ""
    property string fallbackMigrationStatus: "QML landing zone ready"
    property string fallbackLegacyRuntimeStatus: "Existing QWidget workspace remains active."
    property string architectureStatus: "Catalog-driven placeholder"
    property string architectureSummary: "This workspace now binds through the maintenance QML catalog and is ready for workflow-by-workflow migration."
    readonly property var workspaceModel: root.maintenanceCatalog
        ? root.maintenanceCatalog.workspace(root.routeId)
        : ({
            "routeId": root.routeId,
            "title": root.fallbackTitle,
            "summary": root.fallbackSummary,
            "migrationStatus": root.fallbackMigrationStatus,
            "legacyRuntimeStatus": root.fallbackLegacyRuntimeStatus
        })

    title: root.workspaceModel.title
    subtitle: root.workspaceModel.summary

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            MaintenanceWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceModel.migrationStatus || ""
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: root.architectureStatus
                architectureSummary: root.architectureSummary
            }
        }
    }
}
