import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementFinancialsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.financialsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.financials",
            "title": "Financials",
            "summary": "Project cost, labor, baseline budget, and financial reporting workflows.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget financials workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    FinancialsDialogHost {
        id: dialogHost

        selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
        taskOptions: root.workspaceController ? (root.workspaceController.taskOptions || []) : []
        costTypeOptions: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createCostItem(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateCostItem(payload)
            }
        }

        onDeleteRequested: function(costId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteCostItem(costId)
            }
        }
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

            FinancialsMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML financials operations slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Cost-item CRUD, finance KPI summary, cashflow, ledger trail, and analytics now run through a typed PM controller backed by the financials desktop API."
            }

            FinancialsFiltersSection {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                costTypeOptions: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                selectedCostType: root.workspaceController ? root.workspaceController.selectedCostType : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onProjectUpdated: function(projectId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(projectId)
                    }
                }

                onCostTypeUpdated: function(costType) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setCostTypeFilter(costType)
                    }
                }

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateRequested: function() {
                    dialogHost.openCreateDialog()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                FinancialsCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    costsModel: root.workspaceController ? root.workspaceController.costs : ({})
                    selectedCostId: root.workspaceController ? root.workspaceController.selectedCostId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onCostSelected: function(costId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectCost(costId)
                        }
                    }

                    onEditRequested: function(costData) {
                        if (costData && costData.id && root.workspaceController !== null) {
                            root.workspaceController.selectCost(costData.id)
                        }
                        dialogHost.openEditDialog(costData)
                    }

                    onDeleteRequested: function(costData) {
                        if (costData && costData.id && root.workspaceController !== null) {
                            root.workspaceController.selectCost(costData.id)
                        }
                        dialogHost.openDeleteDialog(costData)
                    }
                }

                FinancialsDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    costDetail: root.workspaceController ? root.workspaceController.selectedCost : ({})
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.workspaceController ? root.workspaceController.selectedCost : ({}))
                    onDeleteRequested: dialogHost.openDeleteDialog(root.workspaceController ? root.workspaceController.selectedCost : ({}))
                }
            }

            FinancialsInsightsSection {
                Layout.fillWidth: true
                cashflowModel: root.workspaceController ? root.workspaceController.cashflow : ({})
                ledgerModel: root.workspaceController ? root.workspaceController.ledger : ({})
                sourceAnalyticsModel: root.workspaceController ? root.workspaceController.sourceAnalytics : ({})
                costTypeAnalyticsModel: root.workspaceController ? root.workspaceController.costTypeAnalytics : ({})
                notes: root.workspaceController ? (root.workspaceController.notes || []) : []
            }
        }
    }
}
