import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementDashboardWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.dashboardWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.dashboard",
            "title": "Inventory Dashboard",
            "summary": "Inventory KPIs, low-stock watchlists, procurement queues, and receiving pressure.",
            "migrationStatus": "QML dashboard slice active",
            "legacyRuntimeStatus": "Existing QWidget dashboard remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": "Inventory overview and procurement pressure appear here once the desktop API is connected.",
            "metrics": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            InventoryWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            Text {
                Layout.fillWidth: true
                text: root.workspaceController ? root.workspaceController.contextLabel : ""
                color: Theme.AppTheme.textMuted
                visible: text.length > 0
                wrapMode: Text.WordWrap
            }

            DashboardMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            InventoryWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceModel.migrationStatus || ""
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Dashboard desktop API"
                architectureSummary: "Low-stock watch, approval queue, and receiving queue now render through the typed inventory QML catalog."
            }

            DashboardSections {
                Layout.fillWidth: true
                sections: root.workspaceController ? root.workspaceController.sections : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }
        }
    }
}
