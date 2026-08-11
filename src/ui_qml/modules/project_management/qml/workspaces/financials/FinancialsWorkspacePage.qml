pragma ComponentBehavior: Bound

import QtQuick
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "dialogs" as Dialogs
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementFinancialsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.financialsWorkspace : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({ "routeId": "project_management.financials", "title": "Financials", "summary": "Project financial control and reporting." })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": root.workspaceModel.title, "subtitle": root.workspaceModel.summary, "metrics": [] })
    readonly property var cashflowModel: root.workspaceController
        ? root.workspaceController.cashflow : ({ "items": [] })
    readonly property var ledgerModel: root.workspaceController
        ? root.workspaceController.ledger : ({ "items": [] })
    readonly property var sourceAnalyticsModel: root.workspaceController
        ? root.workspaceController.sourceAnalytics : ({ "items": [] })
    readonly property var baselineVarianceModel: root.workspaceController
        ? (root.workspaceController.baselineVariance || []) : []

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    readonly property var detailPage: detailPageLoader.item
    property int _pendingDetailSection: 0

    readonly property bool _hasProcPoCap: root.pmCatalog
        ? root.pmCatalog.hasCapability("procurement.purchase_orders.read") : false
    readonly property var _detailSections: {
        const sections = [
            "Profile", "Budget Versions", "Budget Lines", "Rate Cards", "Planned Costs",
            "Actuals", "Forecast", "Commitments", "Invoices"
        ]
        if (root._hasProcPoCap) sections.push("Purchase Orders")
        sections.push("Earned Value")
        sections.push("Variance")
        sections.push("Activity")
        return sections
    }
    readonly property string _activeDetailSection: {
        if (!root.detailPage) return ""
        const index = root.detailPage.activeSectionIndex
        return index >= 0 && index < root._detailSections.length
            ? String(root._detailSections[index]) : ""
    }
    readonly property var _detailActions: root._activeDetailSection === "Actuals" ? [
        {
            "id": "add_manual_actual",
            "label": "New Manual Actual",
            "icon": "add",
            "enabled": root.workspaceController
                ? root.workspaceController.selectedProjectId.length > 0
                    && (root.workspaceController.manualActualOptions.costCodes || []).length > 0
                : false,
            "danger": false
        }
    ] : []

    function _selectedProjectLabel() {
        const selectedId = root.workspaceController ? root.workspaceController.selectedProjectId : ""
        const options = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
        for (let index = 0; index < options.length; index++) {
            if (String(options[index].value || "") === String(selectedId || "")) {
                return String(options[index].label || "")
            }
        }
        return ""
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.FinancialsDialogHost {
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                taskOptions: root.workspaceController ? (root.workspaceController.taskOptions || []) : []
                manualActualOptions: root.workspaceController
                    ? (root.workspaceController.manualActualOptions || {}) : ({})
                workspaceController: root.workspaceController
            }
        }
    }

    Loader {
        id: detailPageLoader
        anchors.fill: parent
        active: true
        asynchronous: true
        sourceComponent: Component {
            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: root._detailSections
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width: parent ? parent.width : 0
                    showBack: false
                    title: root._activeDetailSection || "Project Finance"
                    subtitle: root._selectedProjectLabel()
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions
                    onActionTriggered: function(actionId) {
                        if (actionId === "add_manual_actual") {
                            dialogHostLoader.invoke("openCreateManualActualDialog")
                        }
                    }
                }

                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.FinancialsDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    cashflowModel: root.cashflowModel
                    ledgerModel: root.ledgerModel
                    ledgerTableModel: root.workspaceController ? root.workspaceController.ledgerTableModel : null
                    sourceAnalyticsModel: root.sourceAnalyticsModel
                    overviewModel: root.overviewModel
                    forecastModel: root.workspaceController ? root.workspaceController.forecast : ({})
                    commitmentSummaryModel: root.workspaceController ? root.workspaceController.commitmentSummary : ({})
                    commitmentsModel: root.workspaceController ? root.workspaceController.commitments : ({})
                    commitmentsTableModel: root.workspaceController ? root.workspaceController.commitmentsTableModel : null
                    baselineVarianceModel: root.baselineVarianceModel
                    financialProfileModel: root.workspaceController ? root.workspaceController.financialProfile : ({})
                    budgetVersionsModel: root.workspaceController ? root.workspaceController.budgetVersions : ({ "items": [] })
                    budgetLinesModel: root.workspaceController ? root.workspaceController.budgetLines : ({ "items": [] })
                    rateCardsModel: root.workspaceController ? root.workspaceController.rateCards : ({ "items": [] })
                    rateLinesModel: root.workspaceController ? root.workspaceController.rateLines : ({ "items": [] })
                    plannedCostVersionsModel: root.workspaceController ? root.workspaceController.plannedCostVersions : ({ "items": [] })
                    plannedCostLinesModel: root.workspaceController ? root.workspaceController.plannedCostLines : ({ "items": [] })
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onConfigurationPageRequested: function(collection, page) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setConfigurationPage(collection, page)
                        }
                    }
                }
            }
        }
    }
}
