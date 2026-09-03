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
    readonly property var costPhasingModel: root.workspaceController
        ? root.workspaceController.costPhasing : ({ "items": [] })
    readonly property var ledgerModel: root.workspaceController
        ? root.workspaceController.ledger : ({ "items": [] })
    readonly property var activityModel: root.workspaceController
        ? root.workspaceController.activity : ({ "items": [] })
    readonly property var baselineVarianceModel: root.workspaceController
        ? (root.workspaceController.baselineVariance || []) : []

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    readonly property var detailPage: detailPageLoader.item
    property int _pendingDetailSection: 0
    property string _selectedActualEntryId: ""
    property string _selectedProjectLabelText: ""

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
            "Overview",
            "Planning",
            "Costs",
            "Performance",
            "Commercial",
            "Controls"
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
                && root.workspaceController.activeDestination === "controls"
                && root.workspaceController.activeSubsection === "setup") return root.workspaceController.canCreateCostCode ? [
            {
                "id": "add_cost_code",
                "label": "New Cost Code",
                "icon": "add",
                "enabled": !root.workspaceController.isBusy,
                "danger": false
            }
        ] : []
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
                    "enabled": !busy,
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
        if (root._selectedProjectLabelText.length > 0)
            return root._selectedProjectLabelText
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
                selectedProjectLabel: root._selectedProjectLabel()
                manualActualDefaults: root.workspaceController
                    ? (root.workspaceController.manualActualDefaults || {}) : ({})
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

                        AppControls.SearchablePagedSelector {
                            id: projectScopeSelector
                            Layout.preferredWidth: 300
                            Layout.maximumWidth: 420
                            Layout.fillWidth: true
                            placeholderText: "Select a project"
                            searchPlaceholder: "Search project name or code..."
                            contextKey: "finance-projects"
                            enabled: root.workspaceController !== null
                                && !root.workspaceController.isBusy
                            function syncSelection() {
                                const selectedId = root.workspaceController
                                    ? root.workspaceController.selectedProjectId : ""
                                const options = root.workspaceController
                                    ? (root.workspaceController.projectOptions || []) : []
                                for (let index = 0; index < options.length; index += 1) {
                                    if (String(options[index].value || "") === String(selectedId || "")) {
                                        projectScopeSelector.setResolvedItem(options[index])
                                        root._selectedProjectLabelText = String(options[index].label || "")
                                        return
                                    }
                                }
                            }

                            Component.onCompleted: syncSelection()

                            onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                                const result = root.workspaceController
                                    ? root.workspaceController.searchFinanceProjects(query, page, pageSize)
                                    : ({ "ok": false, "message": "Finance controller is unavailable." })
                                projectScopeSelector.acceptResult(result, generation, lookupContext)
                            }
                            onSelectionChanged: function(value, label) {
                                root._selectedProjectLabelText = label
                                if (root.workspaceController !== null)
                                    root.workspaceController.selectProject(value)
                            }
                        }

                        Connections {
                            target: root.workspaceController
                            function onProjectOptionsChanged() { projectScopeSelector.syncSelection() }
                            function onSelectedProjectIdChanged() { projectScopeSelector.syncSelection() }
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
                        if (actionId === "add_cost_code") {
                            dialogHostLoader.invoke("openCostCodeDialog", "create", null)
                            return
                        }
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
                    costPhasingModel: root.costPhasingModel
                    costPhasingBasisModel: root.workspaceController ? root.workspaceController.costPhasingBasis : ({ "fields": [] })
                    evmBasisModel: root.workspaceController ? root.workspaceController.evmBasis : ({ "fields": [] })
                    evmMetricsModel: root.workspaceController ? root.workspaceController.evmMetrics : ({ "items": [] })
                    varianceMetricsModel: root.workspaceController ? root.workspaceController.varianceMetrics : ({ "items": [] })
                    reportDefinitionsModel: root.workspaceController ? root.workspaceController.reportDefinitions : ({ "items": [] })
                    costPhasingDateFrom: root.workspaceController ? root.workspaceController.costPhasingDateFrom : ""
                    costPhasingDateTo: root.workspaceController ? root.workspaceController.costPhasingDateTo : ""
                    costPhasingGranularity: root.workspaceController ? root.workspaceController.costPhasingGranularity : "month"
                    onCostPhasingPresetRequested: function(months, granularity) {
                        if (root.workspaceController) root.workspaceController.setCostPhasingPreset(months, granularity)
                    }
                    ledgerModel: root.ledgerModel
                    activityModel: root.activityModel
                    ledgerTableModel: root.workspaceController ? root.workspaceController.ledgerTableModel : null
                    selectedActualEntryId: root._selectedActualEntryId
                    actualSortKey: root.workspaceController ? root.workspaceController.actualSortKey : "metaText"
                    actualSortDirection: root.workspaceController ? root.workspaceController.actualSortDirection : Qt.DescendingOrder
                    onActualEntrySelected: function(entryId) { root._selectedActualEntryId = entryId }
                    overviewModel: root.overviewModel
                    forecastVersionsModel: root.workspaceController ? root.workspaceController.forecastVersions : ({ "items": [] })
                    forecastLinesModel: root.workspaceController ? root.workspaceController.forecastLines : ({ "items": [] })
                    selectedForecastModel: root.workspaceController ? root.workspaceController.selectedForecast : ({ "id": "", "fields": [] })
                    forecastVersionsTableModel: root.workspaceController ? root.workspaceController.forecastVersionsTableModel : null
                    forecastLinesTableModel: root.workspaceController ? root.workspaceController.forecastLinesTableModel : null
                    selectedForecastId: root.workspaceController ? root.workspaceController.selectedForecastId : ""
                    forecastVersionSortKey: root.workspaceController ? root.workspaceController.forecastVersionSortKey : "revision"
                    forecastVersionSortDirection: root.workspaceController ? root.workspaceController.forecastVersionSortDirection : Qt.DescendingOrder
                    forecastLineSortKey: root.workspaceController ? root.workspaceController.forecastLineSortKey : "title"
                    forecastLineSortDirection: root.workspaceController ? root.workspaceController.forecastLineSortDirection : Qt.AscendingOrder
                    forecastVersionSearch: root.workspaceController ? root.workspaceController.forecastVersionSearch : ""
                    forecastVersionStatus: root.workspaceController ? root.workspaceController.forecastVersionStatus : ""
                    forecastGenerationMode: root.workspaceController ? root.workspaceController.forecastGenerationMode : ""
                    forecastLineSearch: root.workspaceController ? root.workspaceController.forecastLineSearch : ""
                    forecastLineSourceType: root.workspaceController ? root.workspaceController.forecastLineSourceType : ""
                    showGenerateForecast: root.workspaceController ? root.workspaceController.showGenerateForecast : false
                    canGenerateForecast: root.workspaceController ? root.workspaceController.canGenerateForecast : false
                    generateForecastDisabledReason: root.workspaceController ? root.workspaceController.generateForecastDisabledReason : ""
                    financialChangesModel: root.workspaceController ? root.workspaceController.financialChanges : ({ "items": [] })
                    financialChangeImpactsModel: root.workspaceController ? root.workspaceController.financialChangeImpacts : ({ "items": [] })
                    selectedChangeModel: root.workspaceController ? root.workspaceController.selectedChange : ({ "id": "", "fields": [] })
                    canCreateFinancialChange: root.workspaceController
                        ? root.workspaceController.canCreateFinancialChange : false
                    financialChangesTableModel: root.workspaceController ? root.workspaceController.financialChangesTableModel : null
                    financialChangeImpactsTableModel: root.workspaceController ? root.workspaceController.financialChangeImpactsTableModel : null
                    selectedChangeId: root.workspaceController ? root.workspaceController.selectedChangeId : ""
                    changeSortKey: root.workspaceController ? root.workspaceController.changeSortKey : "metaText"
                    changeSortDirection: root.workspaceController ? root.workspaceController.changeSortDirection : Qt.DescendingOrder
                    impactSortKey: root.workspaceController ? root.workspaceController.impactSortKey : "metaText"
                    impactSortDirection: root.workspaceController ? root.workspaceController.impactSortDirection : Qt.AscendingOrder
                    changeSearch: root.workspaceController ? root.workspaceController.changeSearch : ""
                    changeStatus: root.workspaceController ? root.workspaceController.changeStatus : ""
                    changeApprovalStatus: root.workspaceController ? root.workspaceController.changeApprovalStatus : ""
                    changeAppliedState: root.workspaceController ? root.workspaceController.changeAppliedState : ""
                    impactSearch: root.workspaceController ? root.workspaceController.impactSearch : ""
                    impactType: root.workspaceController ? root.workspaceController.impactType : ""
                    impactAppliedState: root.workspaceController ? root.workspaceController.impactAppliedState : ""
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
                    setupCostCodesModel: root.workspaceController ? root.workspaceController.setupCostCodes : ({"items":[]})
                    setupRestrictionsModel: root.workspaceController ? root.workspaceController.setupRestrictions : ({"items":[]})
                    setupCostCodesTableModel: root.workspaceController ? root.workspaceController.setupCostCodesTableModel : null
                    setupRestrictionsTableModel: root.workspaceController ? root.workspaceController.setupRestrictionsTableModel : null
                    canManageCostCodeRestrictions: root.workspaceController ? root.workspaceController.canManageCostCodeRestrictions : false
                    setupCostCodeSortKey: root.workspaceController ? root.workspaceController.setupCostCodeSortKey : "code"
                    setupCostCodeSortDirection: root.workspaceController ? root.workspaceController.setupCostCodeSortDirection : Qt.AscendingOrder
                    setupRestrictionSortKey: root.workspaceController ? root.workspaceController.setupRestrictionSortKey : "code"
                    setupRestrictionSortDirection: root.workspaceController ? root.workspaceController.setupRestrictionSortDirection : Qt.AscendingOrder
                    setupCostCodeSearch: root.workspaceController ? root.workspaceController.setupCostCodeSearch : ""
                    setupCostCodeStatus: root.workspaceController ? root.workspaceController.setupCostCodeStatus : ""
                    setupCostCodeAssignment: root.workspaceController ? root.workspaceController.setupCostCodeAssignment : ""
                    setupRestrictionSearch: root.workspaceController ? root.workspaceController.setupRestrictionSearch : ""
                    budgetVersionsModel: root.workspaceController ? root.workspaceController.budgetVersions : ({ "items": [] })
                    budgetLinesModel: root.workspaceController ? root.workspaceController.budgetLines : ({ "items": [] })
                    budgetVersionsTableModel: root.workspaceController ? root.workspaceController.budgetVersionsTableModel : null
                    budgetLinesTableModel: root.workspaceController ? root.workspaceController.budgetLinesTableModel : null
                    selectedBudgetId: root.workspaceController ? root.workspaceController.selectedBudgetId : ""
                    showCreateBudgetVersion: root.workspaceController
                        ? root.workspaceController.showCreateBudgetVersion : false
                    canCreateBudgetVersion: root.workspaceController
                        ? root.workspaceController.canCreateBudgetVersion : false
                    createBudgetVersionDisabledReason: root.workspaceController
                        ? root.workspaceController.createBudgetVersionDisabledReason : ""
                    budgetVersionSortKey: root.workspaceController ? root.workspaceController.budgetVersionSortKey : "revision"
                    budgetVersionSortDirection: root.workspaceController ? root.workspaceController.budgetVersionSortDirection : Qt.DescendingOrder
                    budgetLineSortKey: root.workspaceController ? root.workspaceController.budgetLineSortKey : "metaText"
                    budgetLineSortDirection: root.workspaceController ? root.workspaceController.budgetLineSortDirection : Qt.DescendingOrder
                    rateCardsModel: root.workspaceController ? root.workspaceController.rateCards : ({ "items": [] })
                    rateLinesModel: root.workspaceController ? root.workspaceController.rateLines : ({ "items": [] })
                    selectedRateCardModel: root.workspaceController ? root.workspaceController.selectedRateCard : ({ "id": "", "fields": [] })
                    rateCardsTableModel: root.workspaceController ? root.workspaceController.rateCardsTableModel : null
                    rateLinesTableModel: root.workspaceController ? root.workspaceController.rateLinesTableModel : null
                    selectedRateCardId: root.workspaceController ? root.workspaceController.selectedRateCardId : ""
                    rateCardSortKey: root.workspaceController ? root.workspaceController.rateCardSortKey : "title"
                    rateCardSortDirection: root.workspaceController ? root.workspaceController.rateCardSortDirection : Qt.AscendingOrder
                    rateLineSortKey: root.workspaceController ? root.workspaceController.rateLineSortKey : "title"
                    rateLineSortDirection: root.workspaceController ? root.workspaceController.rateLineSortDirection : Qt.AscendingOrder
                    rateCardSearch: root.workspaceController ? root.workspaceController.rateCardSearch : ""
                    rateCardScope: root.workspaceController ? root.workspaceController.rateCardScope : ""
                    rateCardStatus: root.workspaceController ? root.workspaceController.rateCardStatus : ""
                    rateLineSearch: root.workspaceController ? root.workspaceController.rateLineSearch : ""
                    rateLineRateType: root.workspaceController ? root.workspaceController.rateLineRateType : ""
                    rateLineStatus: root.workspaceController ? root.workspaceController.rateLineStatus : ""
                    rateLineEffectiveStatus: root.workspaceController ? root.workspaceController.rateLineEffectiveStatus : ""
                    plannedCostVersionsModel: root.workspaceController ? root.workspaceController.plannedCostVersions : ({ "items": [] })
                    plannedCostLinesModel: root.workspaceController ? root.workspaceController.plannedCostLines : ({ "items": [] })
                    plannedCostVersionsTableModel: root.workspaceController ? root.workspaceController.plannedCostVersionsTableModel : null
                    plannedCostLinesTableModel: root.workspaceController ? root.workspaceController.plannedCostLinesTableModel : null
                    selectedPlannedCostVersionId: root.workspaceController ? root.workspaceController.selectedPlannedCostVersionId : ""
                    plannedCostVersionSortKey: root.workspaceController ? root.workspaceController.plannedCostVersionSortKey : "revision"
                    plannedCostVersionSortDirection: root.workspaceController ? root.workspaceController.plannedCostVersionSortDirection : Qt.DescendingOrder
                    plannedCostLineSortKey: root.workspaceController ? root.workspaceController.plannedCostLineSortKey : "title"
                    plannedCostLineSortDirection: root.workspaceController ? root.workspaceController.plannedCostLineSortDirection : Qt.AscendingOrder
                    billingProfileModel: root.workspaceController ? root.workspaceController.billingProfile : ({ "id": "", "fields": [] })
                    billingScheduleModel: root.workspaceController ? root.workspaceController.billingSchedule : ({ "items": [] })
                    billingPreparationsModel: root.workspaceController ? root.workspaceController.billingPreparations : ({ "items": [] })
                    billingPreparationLinesModel: root.workspaceController ? root.workspaceController.billingPreparationLines : ({ "items": [] })
                    selectedBillingPreparationModel: root.workspaceController ? root.workspaceController.selectedBillingPreparation : ({ "id": "", "fields": [] })
                    billingScheduleTableModel: root.workspaceController ? root.workspaceController.billingScheduleTableModel : null
                    billingPreparationsTableModel: root.workspaceController ? root.workspaceController.billingPreparationsTableModel : null
                    billingPreparationLinesTableModel: root.workspaceController ? root.workspaceController.billingPreparationLinesTableModel : null
                    selectedBillingPreparationId: root.workspaceController ? root.workspaceController.selectedBillingPreparationId : ""
                    billingScheduleSortKey: root.workspaceController ? root.workspaceController.billingScheduleSortKey : "supportingText"
                    billingScheduleSortDirection: root.workspaceController ? root.workspaceController.billingScheduleSortDirection : Qt.AscendingOrder
                    billingPreparationSortKey: root.workspaceController ? root.workspaceController.billingPreparationSortKey : "metaText"
                    billingPreparationSortDirection: root.workspaceController ? root.workspaceController.billingPreparationSortDirection : Qt.DescendingOrder
                    billingLineSortKey: root.workspaceController ? root.workspaceController.billingLineSortKey : "metaText"
                    billingLineSortDirection: root.workspaceController ? root.workspaceController.billingLineSortDirection : Qt.AscendingOrder
                    billingScheduleSearch: root.workspaceController ? root.workspaceController.billingScheduleSearch : ""
                    billingScheduleStatus: root.workspaceController ? root.workspaceController.billingScheduleStatus : ""
                    billingScheduleSourceState: root.workspaceController ? root.workspaceController.billingScheduleSourceState : ""
                    billingPreparationSearch: root.workspaceController ? root.workspaceController.billingPreparationSearch : ""
                    billingPreparationStatus: root.workspaceController ? root.workspaceController.billingPreparationStatus : ""
                    billingPreparationMethod: root.workspaceController ? root.workspaceController.billingPreparationMethod : ""
                    billingPreparationApprovalStatus: root.workspaceController ? root.workspaceController.billingPreparationApprovalStatus : ""
                    billingPreparationDeliveryState: root.workspaceController ? root.workspaceController.billingPreparationDeliveryState : ""
                    billingPreparationCorrectionState: root.workspaceController ? root.workspaceController.billingPreparationCorrectionState : ""
                    billingLineSearch: root.workspaceController ? root.workspaceController.billingLineSearch : ""
                    billingLineSourceType: root.workspaceController ? root.workspaceController.billingLineSourceType : ""
                    billingLineSourceState: root.workspaceController ? root.workspaceController.billingLineSourceState : ""
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
                    onSetupProfileEditRequested: function(profile) { dialogHostLoader.invoke("openFinancialProfileDialog", profile) }
                    onSetupProfileTransitionRequested: function(action, profile) { dialogHostLoader.invoke("openFinancialSetupLifecycleDialog", action, profile, null, null) }
                    onSetupCostCodeEditRequested: function(costCode) { dialogHostLoader.invoke("openCostCodeDialog", "edit", costCode) }
                    onSetupCostCodeStatusRequested: function(action, costCode) { dialogHostLoader.invoke("openFinancialSetupLifecycleDialog", action, null, costCode, null) }
                    onSetupRestrictionAddRequested: dialogHostLoader.invoke("openCostCodeRestrictionDialog")
                    onSetupRestrictionRemoveRequested: function(restriction) { dialogHostLoader.invoke("openFinancialSetupLifecycleDialog", "remove_restriction", null, null, restriction) }
                    onSetupCostCodePageRequested: function(page) { if (root.workspaceController) root.workspaceController.setSetupCostCodePage(page) }
                    onSetupRestrictionPageRequested: function(page) { if (root.workspaceController) root.workspaceController.setSetupRestrictionPage(page) }
                    onSetupCostCodeSortRequested: function(key, direction) { if (root.workspaceController) root.workspaceController.setSetupCostCodeSort(key, direction) }
                    onSetupRestrictionSortRequested: function(key, direction) { if (root.workspaceController) root.workspaceController.setSetupRestrictionSort(key, direction) }
                    onSetupCostCodeFiltersRequested: function(search, status, assignment) { if (root.workspaceController) root.workspaceController.setSetupCostCodeFilters(search, status, assignment) }
                    onSetupRestrictionFilterRequested: function(search) { if (root.workspaceController) root.workspaceController.setSetupRestrictionFilter(search) }
                    onBudgetVersionSelected: function(budgetId) {
                        if (root.workspaceController !== null) root.workspaceController.selectBudgetVersion(budgetId)
                    }
                    onBudgetVersionPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setBudgetVersionPage(page)
                    }
                    onBudgetVersionSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setBudgetVersionSort(key, direction)
                    }
                    onBudgetLineSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setBudgetLineSort(key, direction)
                    }
                    onBudgetCreateRequested: {
                        dialogHostLoader.invoke("openBudgetVersionDialog", "create", null)
                    }
                    onBudgetEditRequested: function(budget) {
                        dialogHostLoader.invoke("openBudgetVersionDialog", "edit", budget)
                    }
                    onBudgetSuccessorRequested: function(budget) {
                        dialogHostLoader.invoke("openBudgetVersionDialog", "successor", budget)
                    }
                    onBudgetLifecycleRequested: function(action, budget) {
                        dialogHostLoader.invoke("openBudgetLifecycleDialog", action, budget, null)
                    }
                    onBudgetLineAddRequested: function(budget) {
                        dialogHostLoader.invoke("openBudgetLineDialog", "create", budget, null)
                    }
                    onBudgetLineEditRequested: function(budget, line) {
                        dialogHostLoader.invoke("openBudgetLineDialog", "edit", budget, line)
                    }
                    onBudgetLineDeleteRequested: function(budget, line) {
                        dialogHostLoader.invoke("openBudgetLifecycleDialog", "delete_line", budget, line)
                    }
                    onForecastGenerateRequested: {
                        dialogHostLoader.invoke("openForecastGenerationDialog")
                    }
                    onForecastLifecycleRequested: function(action, forecast) {
                        dialogHostLoader.invoke(
                            "openForecastLifecycleDialog", action, forecast
                        )
                    }
                    onFinancialChangeRequestCreateRequested: {
                        dialogHostLoader.invoke(
                            "openFinancialChangeRequestDialog", "create", null
                        )
                    }
                    onFinancialChangeRequestEditRequested: function(change) {
                        dialogHostLoader.invoke(
                            "openFinancialChangeRequestDialog", "edit", change
                        )
                    }
                    onFinancialChangeImpactCreateRequested: function(change) {
                        dialogHostLoader.invoke(
                            "openFinancialChangeImpactDialog", "create", change, null
                        )
                    }
                    onFinancialChangeImpactEditRequested: function(change, impact) {
                        dialogHostLoader.invoke(
                            "openFinancialChangeImpactDialog", "edit", change, impact
                        )
                    }
                    onFinancialChangeLifecycleRequested: function(action, change, impact) {
                        dialogHostLoader.invoke(
                            "openFinancialChangeLifecycleDialog", action, change, impact
                        )
                    }
                    onPlannedCostVersionSelected: function(versionId) {
                        if (root.workspaceController !== null) root.workspaceController.selectPlannedCostVersion(versionId)
                    }
                    onPlannedCostVersionPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setPlannedCostVersionPage(page)
                    }
                    onPlannedCostVersionSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setPlannedCostVersionSort(key, direction)
                    }
                    onPlannedCostLineSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setPlannedCostLineSort(key, direction)
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
                    onForecastVersionPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setForecastVersionPage(page)
                    }
                    onForecastLinePageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setForecastLinePage(page)
                    }
                    onForecastVersionSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setForecastVersionSort(key, direction)
                    }
                    onForecastLineSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setForecastLineSort(key, direction)
                    }
                    onForecastVersionFiltersRequested: function(search, status, generationMode) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setForecastVersionFilters(search, status, generationMode)
                    }
                    onForecastLineFiltersRequested: function(search, sourceType) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setForecastLineFilters(search, sourceType)
                    }
                    onRateCardSelected: function(rateCardId) {
                        if (root.workspaceController !== null) root.workspaceController.selectRateCard(rateCardId)
                    }
                    onRateCardPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setRateCardPage(page)
                    }
                    onRateLinePageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setRateLinePage(page)
                    }
                    onRateCardSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setRateCardSort(key, direction)
                    }
                    onRateLineSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setRateLineSort(key, direction)
                    }
                    onRateCardFiltersRequested: function(search, scope, status) {
                        if (root.workspaceController !== null) root.workspaceController.setRateCardFilters(search, scope, status)
                    }
                    onRateLineFiltersRequested: function(search, rateType, status, effectiveStatus) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setRateLineFilters(search, rateType, status, effectiveStatus)
                    }
                    onFinancialChangeSelected: function(changeId) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectFinancialChange(changeId)
                    }
                    onFinancialChangePageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setFinancialChangePage(page)
                    }
                    onFinancialChangeImpactPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setFinancialChangeImpactPage(page)
                    }
                    onFinancialChangeSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setFinancialChangeSort(key, direction)
                    }
                    onFinancialChangeImpactSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setFinancialChangeImpactSort(key, direction)
                    }
                    onFinancialChangeFiltersRequested: function(search, status, approvalStatus, appliedState) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setFinancialChangeFilters(search, status, approvalStatus, appliedState)
                    }
                    onFinancialChangeImpactFiltersRequested: function(search, impactType, appliedState) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setFinancialChangeImpactFilters(search, impactType, appliedState)
                    }
                    onBillingPreparationSelected: function(preparationId) {
                        if (root.workspaceController !== null) root.workspaceController.selectBillingPreparation(preparationId)
                    }
                    onBillingSchedulePageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingSchedulePage(page)
                    }
                    onBillingPreparationPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingPreparationPage(page)
                    }
                    onBillingLinePageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingLinePage(page)
                    }
                    onBillingScheduleSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingScheduleSort(key, direction)
                    }
                    onBillingPreparationSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingPreparationSort(key, direction)
                    }
                    onBillingLineSortRequested: function(key, direction) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingLineSort(key, direction)
                    }
                    onBillingScheduleFiltersRequested: function(search, status, sourceState) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingScheduleFilters(search, status, sourceState)
                    }
                    onBillingPreparationFiltersRequested: function(search, status, method, approvalStatus, deliveryState, correctionState) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingPreparationFilters(search, status, method, approvalStatus, deliveryState, correctionState)
                    }
                    onBillingLineFiltersRequested: function(search, sourceType, sourceState) {
                        if (root.workspaceController !== null) root.workspaceController.setBillingLineFilters(search, sourceType, sourceState)
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
