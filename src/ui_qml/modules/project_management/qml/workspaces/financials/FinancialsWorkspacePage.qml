pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
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
    readonly property var activityModel: root.workspaceController
        ? root.workspaceController.activity : ({ "items": [] })
    readonly property var sourceAnalyticsModel: root.workspaceController
        ? root.workspaceController.sourceAnalytics : ({ "items": [] })
    readonly property var baselineVarianceModel: root.workspaceController
        ? (root.workspaceController.baselineVariance || []) : []

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    readonly property var detailPage: detailPageLoader.item
    property int _pendingDetailSection: 0
    property string _selectedActualEntryId: ""

    function _selectedActualEntry() {
        const items = (root.ledgerModel.items || [])
        for (let index = 0; index < items.length; index += 1) {
            if (String(items[index].id || "") === root._selectedActualEntryId) {
                return items[index]
            }
        }
        return null
    }

    readonly property var _detailSections: {
        return [
            { "label": "Overview", "group": "Finance" },
            { "label": "Planning", "group": "Finance" },
            { "label": "Costs", "group": "Finance" },
            { "label": "Performance", "group": "Finance" },
            { "label": "Commercial", "group": "Finance" },
            { "label": "Controls", "group": "Finance" }
        ]
    }
    readonly property var _destinationIds: [
        "overview", "planning", "costs", "performance", "commercial", "controls"
    ]
    readonly property string _activeDetailSection: {
        if (!root.detailPage) return ""
        const index = root.detailPage.activeSectionIndex
        if (index < 0 || index >= root._detailSections.length) return ""
        const entry = root._detailSections[index]
        return typeof entry === "string" ? entry : String(entry.label || "")
    }
    readonly property var _detailActions: {
        if (root.workspaceController
                && root.workspaceController.activeDestination === "costs"
                && root.workspaceController.activeSubsection === "actuals") {
            const selected = root._selectedActualEntry()
            const state = selected ? (selected.state || {}) : {}
            const busy = root.workspaceController ? root.workspaceController.isBusy : false
            return [
                {
                    "id": "add_manual_actual",
                    "label": "New Manual Actual",
                    "icon": "add",
                    "enabled": !busy && root.workspaceController
                        ? root.workspaceController.selectedProjectId.length > 0
                            && (root.workspaceController.manualActualOptions.costCodes || []).length > 0
                        : false,
                    "danger": false
                },
                Boolean(state.canSubmit) ? {
                    "id": "submit_actual",
                    "label": "Submit",
                    "icon": "approve",
                    "enabled": !busy,
                    "danger": false
                } : null,
                Boolean(state.canApprove) ? {
                    "id": "approve_actual",
                    "label": "Approve",
                    "icon": "approve",
                    "enabled": !busy,
                    "danger": false
                } : null,
                Boolean(state.canApprove) ? {
                    "id": "reject_actual",
                    "label": "Reject",
                    "icon": "reject",
                    "enabled": !busy,
                    "danger": true
                } : null,
                Boolean(state.canPost) ? {
                    "id": "post_actual",
                    "label": "Post",
                    "icon": "save",
                    "enabled": !busy,
                    "danger": false
                } : null,
                Boolean(state.canReverse) ? {
                    "id": "reverse_actual",
                    "label": "Reverse",
                    "icon": "delete",
                    "enabled": !busy,
                    "danger": true
                } : null
            ].filter(Boolean)
        }
        if (root.workspaceController
                && root.workspaceController.activeDestination === "performance"
                && root.workspaceController.activeSubsection === "reports") return [
            {
                "id": "export_excel",
                "label": "Export Excel",
                "icon": "export",
                "enabled": root.workspaceController
                    ? root.workspaceController.selectedProjectId.length > 0 : false,
                "danger": false
            },
            {
                "id": "export_pdf",
                "label": "Export PDF",
                "icon": "export",
                "enabled": root.workspaceController
                    ? root.workspaceController.selectedProjectId.length > 0 : false,
                "danger": false
            }
        ]
        return []
    }

    FileDialog {
        id: _excelExportDialog
        title: "Export Financial Report to Excel"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)"]
        defaultSuffix: "xlsx"
        onAccepted: {
            if (root.workspaceController !== null)
                root.workspaceController.exportFinancials("xlsx", String(selectedFile || ""))
        }
    }

    FileDialog {
        id: _pdfExportDialog
        title: "Export Financial Report to PDF"
        fileMode: FileDialog.SaveFile
        nameFilters: ["PDF files (*.pdf)"]
        defaultSuffix: "pdf"
        onAccepted: {
            if (root.workspaceController !== null)
                root.workspaceController.exportFinancials("pdf", String(selectedFile || ""))
        }
    }

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

    function _projectOptionIndex() {
        const selectedId = root.workspaceController ? root.workspaceController.selectedProjectId : ""
        const options = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(selectedId || "")) {
                return index
            }
        }
        return options.length > 0 ? 0 : -1
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
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectFinanceDestination(
                            root._destinationIds[activeSectionIndex] || "overview"
                        )
                    }
                }
                onSectionChanged: function(index) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectFinanceDestination(
                            root._destinationIds[index] || "overview"
                        )
                    }
                }

                Rectangle {
                    property bool detailPagePinned: true

                    width: parent ? parent.width : 0
                    implicitHeight: projectScopeRow.implicitHeight + (Theme.AppTheme.spacingSm * 2)
                    color: Theme.AppTheme.surfaceRaised

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        id: projectScopeRow
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        anchors.topMargin: Theme.AppTheme.spacingSm
                        anchors.bottomMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            text: "Project"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.ComboBox {
                            id: projectScopeCombo
                            Layout.preferredWidth: 300
                            Layout.maximumWidth: 420
                            Layout.fillWidth: true
                            model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                            textRole: "label"
                            currentIndex: root._projectOptionIndex()
                            enabled: root.workspaceController !== null
                                && !root.workspaceController.isBusy
                                && (root.workspaceController.projectOptions || []).length > 0

                            onActivated: function(index) {
                                const options = root.workspaceController
                                    ? (root.workspaceController.projectOptions || []) : []
                                if (root.workspaceController !== null && options[index]) {
                                    root.workspaceController.selectProject(String(options[index].value || ""))
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        AppControls.SecondaryButton {
                            text: "Refresh"
                            iconName: "refresh"
                            enabled: root.workspaceController !== null && !root.workspaceController.isBusy
                            onClicked: root.workspaceController.refresh()
                        }
                    }
                }

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
                            return
                        }
                        if (actionId === "export_excel") {
                            _excelExportDialog.open()
                            return
                        }
                        if (actionId === "export_pdf") {
                            _pdfExportDialog.open()
                            return
                        }
                        const selected = root._selectedActualEntry()
                        if (!selected || !root.workspaceController) return
                        const state = selected.state || {}
                        const entryId = String(state.entryId || selected.id || "")
                        const rowVersion = Number(state.rowVersion || 0)
                        if (actionId === "submit_actual") {
                            root.workspaceController.submitActual({ "entryId": entryId, "rowVersion": rowVersion })
                        } else if (actionId === "approve_actual") {
                            root.workspaceController.approveActual({ "entryId": entryId, "rowVersion": rowVersion })
                        } else if (actionId === "reject_actual") {
                            dialogHostLoader.invoke("openActualDecisionDialog", "reject", entryId, rowVersion)
                        } else if (actionId === "post_actual") {
                            dialogHostLoader.invoke("openActualDecisionDialog", "post", entryId, rowVersion)
                        } else if (actionId === "reverse_actual") {
                            dialogHostLoader.invoke("openActualDecisionDialog", "reverse", entryId, rowVersion)
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
                    activeDestination: root.workspaceController
                        ? root.workspaceController.activeDestination : "overview"
                    activeSubsection: root.workspaceController
                        ? root.workspaceController.activeSubsection : "summary"
                    cashflowModel: root.cashflowModel
                    ledgerModel: root.ledgerModel
                    activityModel: root.activityModel
                    ledgerTableModel: root.workspaceController ? root.workspaceController.ledgerTableModel : null
                    selectedActualEntryId: root._selectedActualEntryId
                    actualSortKey: root.workspaceController ? root.workspaceController.actualSortKey : "metaText"
                    actualSortDirection: root.workspaceController ? root.workspaceController.actualSortDirection : Qt.DescendingOrder
                    onActualEntrySelected: function(entryId) { root._selectedActualEntryId = entryId }
                    sourceAnalyticsModel: root.sourceAnalyticsModel
                    costTypeAnalyticsModel: root.workspaceController
                        ? root.workspaceController.costTypeAnalytics : ({ "items": [] })
                    overviewModel: root.overviewModel
                    forecastModel: root.workspaceController ? root.workspaceController.forecast : ({})
                    forecastVersionsModel: root.workspaceController ? root.workspaceController.forecastVersions : ({ "items": [] })
                    forecastLinesModel: root.workspaceController ? root.workspaceController.forecastLines : ({ "items": [] })
                    selectedForecastId: root.workspaceController ? root.workspaceController.selectedForecastId : ""
                    financialChangesModel: root.workspaceController ? root.workspaceController.financialChanges : ({ "items": [] })
                    financialChangeImpactsModel: root.workspaceController ? root.workspaceController.financialChangeImpacts : ({ "items": [] })
                    selectedChangeId: root.workspaceController ? root.workspaceController.selectedChangeId : ""
                    commitmentSummaryModel: root.workspaceController ? root.workspaceController.commitmentSummary : ({})
                    commitmentsModel: root.workspaceController ? root.workspaceController.commitments : ({})
                    commitmentsTableModel: root.workspaceController ? root.workspaceController.commitmentsTableModel : null
                    commitmentSortKey: root.workspaceController ? root.workspaceController.commitmentSortKey : "metaText"
                    commitmentSortDirection: root.workspaceController ? root.workspaceController.commitmentSortDirection : Qt.DescendingOrder
                    baselineVarianceModel: root.baselineVarianceModel
                    baselineVersionsModel: root.workspaceController ? root.workspaceController.baselineVersions : ({ "items": [] })
                    varianceBasisModel: root.workspaceController ? root.workspaceController.varianceBasis : ({ "fields": [] })
                    selectedBaselineId: root.workspaceController ? root.workspaceController.selectedBaselineId : ""
                    reportBasisModel: root.workspaceController ? root.workspaceController.reportBasis : ({ "fields": [] })
                    financialProfileModel: root.workspaceController ? root.workspaceController.financialProfile : ({})
                    budgetVersionsModel: root.workspaceController ? root.workspaceController.budgetVersions : ({ "items": [] })
                    budgetLinesModel: root.workspaceController ? root.workspaceController.budgetLines : ({ "items": [] })
                    rateCardsModel: root.workspaceController ? root.workspaceController.rateCards : ({ "items": [] })
                    rateLinesModel: root.workspaceController ? root.workspaceController.rateLines : ({ "items": [] })
                    plannedCostVersionsModel: root.workspaceController ? root.workspaceController.plannedCostVersions : ({ "items": [] })
                    plannedCostLinesModel: root.workspaceController ? root.workspaceController.plannedCostLines : ({ "items": [] })
                    billingProfileModel: root.workspaceController ? root.workspaceController.billingProfile : ({ "id": "", "fields": [] })
                    billingScheduleModel: root.workspaceController ? root.workspaceController.billingSchedule : ({ "items": [] })
                    billingPreparationsModel: root.workspaceController ? root.workspaceController.billingPreparations : ({ "items": [] })
                    commercialProjectionModel: root.workspaceController
                        ? root.workspaceController.commercialProjection : ({ "id": "", "fields": [] })
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSubsectionRequested: function(subsection) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectFinanceSubsection(subsection)
                    }
                    onConfigurationPageRequested: function(collection, page) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setConfigurationPage(collection, page)
                        }
                    }
                    onActualPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setActualPage(page)
                    }
                    onActualPageSizeRequested: function(pageSize) {
                        if (root.workspaceController !== null) root.workspaceController.setActualPageSize(pageSize)
                    }
                    onActualSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setActualSort(key, direction)
                    }
                    onCommitmentPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setCommitmentPage(page)
                    }
                    onCommitmentPageSizeRequested: function(pageSize) {
                        if (root.workspaceController !== null) root.workspaceController.setCommitmentPageSize(pageSize)
                    }
                    onCommitmentSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setCommitmentSort(key, direction)
                    }
                    onForecastSelected: function(forecastId) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectForecastVersion(forecastId)
                    }
                    onFinancialChangeSelected: function(changeId) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectFinancialChange(changeId)
                    }
                    onVarianceBaselineSelected: function(baselineId) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectVarianceBaseline(baselineId)
                    }
                }
            }
        }
    }
}
