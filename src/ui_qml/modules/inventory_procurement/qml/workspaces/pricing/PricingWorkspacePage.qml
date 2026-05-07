import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementPricingWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.pricingWorkspace
        : null
    property string pendingExportAction: ""
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.pricing",
            "title": "Pricing",
            "summary": "Supplier pricing analysis plus stock and procurement report exports.",
            "migrationStatus": "QML pricing slice active",
            "legacyRuntimeStatus": "Existing QWidget reports workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var stockSignalsModel: root.workspaceController
        ? root.workspaceController.stockSignals
        : ({
            "title": "Stock Status Signals",
            "subtitle": "",
            "emptyState": "Inventory pricing desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var supplierPricingModel: root.workspaceController
        ? root.workspaceController.supplierPricing
        : ({
            "title": "Supplier Price Lines",
            "subtitle": "",
            "emptyState": "Inventory pricing desktop API is not connected in this QML preview.",
            "items": []
        })

    function exportDefaultTarget(actionName) {
        const now = new Date()
        const stamp = String(now.getFullYear())
            + String(now.getMonth() + 1).padStart(2, "0")
            + String(now.getDate()).padStart(2, "0")
            + "_"
            + String(now.getHours()).padStart(2, "0")
            + String(now.getMinutes()).padStart(2, "0")
            + String(now.getSeconds()).padStart(2, "0")
        switch (actionName) {
        case "stockCsv":
            return "inventory-stock-status_" + stamp + ".csv"
        case "stockExcel":
            return "inventory-stock-status_" + stamp + ".xlsx"
        case "procurementCsv":
            return "inventory-procurement-overview_" + stamp + ".csv"
        case "procurementExcel":
            return "inventory-procurement-overview_" + stamp + ".xlsx"
        default:
            return "inventory-report_" + stamp + ".csv"
        }
    }

    function triggerExport(selectedFile) {
        if (root.workspaceController === null) {
            return
        }
        switch (root.pendingExportAction) {
        case "stockCsv":
            root.workspaceController.exportStockStatusCsv(String(selectedFile || ""))
            break
        case "stockExcel":
            root.workspaceController.exportStockStatusExcel(String(selectedFile || ""))
            break
        case "procurementCsv":
            root.workspaceController.exportProcurementOverviewCsv(String(selectedFile || ""))
            break
        case "procurementExcel":
            root.workspaceController.exportProcurementOverviewExcel(String(selectedFile || ""))
            break
        }
    }

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    FileDialog {
        id: exportDialog

        title: root.pendingExportAction.indexOf("Excel") >= 0
            ? "Export Excel Package"
            : "Export CSV Package"
        fileMode: FileDialog.SaveFile
        nameFilters: root.pendingExportAction.indexOf("Excel") >= 0
            ? ["Excel files (*.xlsx)"]
            : ["CSV files (*.csv)"]
        currentFile: root.exportDefaultTarget(root.pendingExportAction)
        onAccepted: root.triggerExport(selectedFile)
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            PricingMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            InventoryWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            InventoryWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML pricing slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Inventory pricing now runs through a typed controller backed by the split pricing desktop API, reusing the module-local reporting infrastructure for stock and procurement export packages."
            }

            PricingFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                supplierOptions: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                limitOptions: root.workspaceController ? (root.workspaceController.limitOptions || []) : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedStoreroomFilter: root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                selectedSupplierFilter: root.workspaceController ? root.workspaceController.selectedSupplierFilter : "all"
                selectedLimitFilter: root.workspaceController ? root.workspaceController.selectedLimitFilter : "200"
                contextLabel: root.workspaceController ? root.workspaceController.contextLabel : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSiteFilterUpdated: function(siteId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSiteFilter(siteId)
                    }
                }

                onStoreroomFilterUpdated: function(storeroomId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStoreroomFilter(storeroomId)
                    }
                }

                onSupplierFilterUpdated: function(supplierId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSupplierFilter(supplierId)
                    }
                }

                onLimitFilterUpdated: function(limitValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setLimitFilter(limitValue)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }

            PricingExportsSection {
                Layout.fillWidth: true
                canExport: root.workspaceController ? root.workspaceController.canExport : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onStockCsvRequested: {
                    root.pendingExportAction = "stockCsv"
                    exportDialog.open()
                }

                onStockExcelRequested: {
                    root.pendingExportAction = "stockExcel"
                    exportDialog.open()
                }

                onProcurementCsvRequested: {
                    root.pendingExportAction = "procurementCsv"
                    exportDialog.open()
                }

                onProcurementExcelRequested: {
                    root.pendingExportAction = "procurementExcel"
                    exportDialog.open()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                PricingStockSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    stockSignalsModel: root.stockSignalsModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                }

                PricingSupplierPricingSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    supplierPricingModel: root.supplierPricingModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                }
            }
        }
    }
}
