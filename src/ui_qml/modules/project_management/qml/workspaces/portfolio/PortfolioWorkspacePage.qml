pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "panels" as Panels
import "sections" as Sections

AppLayouts.WorkspaceFrame {
    id: root

    // ── Controller wiring ──────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController:
        root.pmCatalog ? root.pmCatalog.portfolioWorkspace : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Portfolio", "subtitle": "", "metrics": [] })

    title:    root.overviewModel.title    || "Portfolio"
    subtitle: root.overviewModel.subtitle || ""

    // ── State ─────────────────────────────────────────────────────────
    PortfolioWorkspaceState {
        id: state
        workspaceController: root.workspaceController
    }

    // ── Detail-page context actions (depend on detailPageLoader.item) ──
    readonly property var _detailActions: {
        const idx = detailPageLoader.item ? detailPageLoader.item.activeSectionIndex : 0
        if (idx === 0)
            return [{ "id": "evaluate", "label": "Evaluate", "icon": "approve", "enabled": true, "danger": false }]
        return []
    }

    // ══════════════════════════════════════════════════════════════════
    //  Stacked layout: list page / detail page
    // ══════════════════════════════════════════════════════════════════
    Item {
        anchors.fill: parent

        // ── List page ─────────────────────────────────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !state.detailOpen

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    loading: root.workspaceController
                        ? root.workspaceController.isBusy
                            && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    message: "Saving changes..."
                    compact: true
                    modal: false
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Sections.PortfolioGovernanceToolbar {
                    Layout.fillWidth: true
                    scenarioOptions:          root.workspaceController ? (root.workspaceController.scenarioOptions || []) : []
                    selectedScenarioId:       root.workspaceController ? root.workspaceController.selectedScenarioId : ""
                    selectedBaseScenarioId:   root.workspaceController ? root.workspaceController.selectedBaseScenarioId : ""
                    selectedCompareScenarioId: root.workspaceController ? root.workspaceController.selectedCompareScenarioId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onScenarioSelected:       function(id) { if (root.workspaceController !== null) root.workspaceController.selectScenario(id) }
                    onCompareBaseSelected:    function(id) { if (root.workspaceController !== null) root.workspaceController.selectCompareBase(id) }
                    onCompareScenarioSelected: function(id) { if (root.workspaceController !== null) root.workspaceController.selectCompareScenario(id) }
                    onRefreshRequested:       { if (root.workspaceController !== null) root.workspaceController.refresh() }
                    onCompareRequested:       { state.bottomTab = 2 }
                    onRebalanceRequested:     { if (root.workspaceController !== null) root.workspaceController.refresh() }
                    onExportRequested:        { if (root.workspaceController !== null) root.workspaceController.exportPortfolio() }
                }

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchText:        root.workspaceController ? root.workspaceController.heatmapSearchText : ""
                    searchPlaceholder: "Search portfolio projects..."
                    showRefresh: true
                    showExport:  true
                    showFilter:  true
                    showCreate:  false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setHeatmapSearchText(text)
                        state.selectedRowIds = []
                    }
                    onFilterClicked:   filterPopup.open()
                    onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
                    onExportRequested:  { if (root.workspaceController !== null) root.workspaceController.exportPortfolio() }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: _heatmapTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect:    true
                        columns:        state.heatmapColumns
                        sourceModel:    root.workspaceController ? root.workspaceController.heatmapTableModel : null
                        loading:        root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText:      state.heatmapModel.emptyState || "No portfolio projects available."
                        selectedRowId:  state.selectedRowId
                        selectedRowIds: state.selectedRowIds

                        onRowSelected: function(rowId) { state.selectedRowId = rowId }
                        onRowActivated: function(rowId) {
                            state.selectedRowId = rowId
                            state.pendingDetailSection = 0
                            state.detailOpen = true
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            const ids = state.selectedRowIds.slice()
                            const idx = ids.indexOf(rowId)
                            if (selected && idx < 0)         ids.push(rowId)
                            else if (!selected && idx >= 0)  ids.splice(idx, 1)
                            state.selectedRowIds = ids
                        }
                        onSelectAllToggled: function(allSelected) {
                            state.selectedRowIds = allSelected
                                ? (root.workspaceController ? (root.workspaceController.heatmapVisibleRowIds || []) : [])
                                : []
                        }
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _bottomPanel.top
                        currentPage: root.workspaceController ? root.workspaceController.heatmapPage : 1
                        pageSize:    root.workspaceController ? root.workspaceController.heatmapPageSize : 25
                        totalItems:  root.workspaceController ? root.workspaceController.heatmapTotalCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setHeatmapPage(page)
                        }
                        onPageSizeRequested: function(ps) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setHeatmapPageSize(ps)
                        }
                    }

                    AppWidgets.BulkActionBar {
                        id: _bulkBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom:       _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: state.selectedRowIds.length
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [{ "id": "evaluate", "label": "Evaluate Scenario", "icon": "approve", "danger": false, "enabled": true }]
                        onCancelRequested:   { state.selectedRowIds = [] }
                        onActionTriggered:   function(actionId) { if (actionId === "evaluate") state.bottomTab = 2 }
                    }

                    // ── Intake status filter popup ─────────────────────
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem:  tableToolbar.filterButtonItem
                        width:       280
                        padding:     Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color:  Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text:           "Intake Status"
                                font.bold:      true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family:    Theme.AppTheme.fontFamily
                                color:          Theme.AppTheme.textMuted
                            }

                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model:    root.workspaceController ? (root.workspaceController.intakeStatusOptions || []) : []
                                textRole: "label"
                                enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: state.optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.intakeStatusOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedIntakeStatusFilter : "all"
                                )
                                onActivated: function(idx) {
                                    const opts = root.workspaceController ? (root.workspaceController.intakeStatusOptions || []) : []
                                    if (root.workspaceController !== null && opts[idx])
                                        root.workspaceController.setIntakeStatusFilter(String(opts[idx].value || "all"))
                                }
                            }

                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text:     "Clear Filters"
                                iconName: "delete"
                                enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onClicked: {
                                    if (root.workspaceController !== null)
                                        root.workspaceController.setIntakeStatusFilter("all")
                                    filterPopup.close()
                                }
                            }
                        }
                    }

                    Panels.PortfolioBottomPanel {
                        id: _bottomPanel
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        height: 268
                        workspaceController: root.workspaceController
                        bottomTab:           state.bottomTab
                        selectedFundingId:   state.selectedFundingId
                        intakeModel:         state.intakeModel
                        dependenciesModel:   state.dependenciesModel
                        capacityPoolModel:   state.capacityPoolModel
                        templatesModel:      state.templatesModel
                        activityItems:       state.activityItems
                        recentActionsModel:  state.recentActionsModel
                        onBottomTabRequested:         function(tab) { state.bottomTab = tab }
                        onSelectedFundingIdRequested: function(id)  { state.selectedFundingId = id }
                    }
                }
            }
        }

        AppWidgets.LoadingOverlay {
            anchors.fill: _listPage
            z: 15
            loading: _listPage.visible
                && (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading portfolio data..."
        }

        // ── Detail page ───────────────────────────────────────────────
        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active:       state.detailOpen
            visible:      state.detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open:        true
                anchors.fill: parent
                showHeader:  false
                showEdit:    false
                showDelete:  false
                isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                sections:    ["Overview", "Scenarios", "Dependencies", "Funding", "Activity"]
                z:           20
                Component.onCompleted: scrollToSection(state.pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    state.selectedHeatmapItem
                        ? String(state.selectedHeatmapItem.title || "Project Details")
                        : "Project Details"
                    subtitle: state.selectedHeatmapItem
                        ? String(state.selectedHeatmapItem.subtitle || "")
                        : ""
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  root._detailActions
                    onBackRequested: state.detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "evaluate") {
                            state.detailOpen = false
                            state.bottomTab = 2
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    width:   parent ? parent.width : 0
                    visible: state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone:    "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width:   parent ? parent.width : 0
                    visible: state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone:    "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.PortfolioDetailPanel {
                    width:             parent ? parent.width : 0
                    detailPage:        detailPageLoader.item
                    heatmapItem:       state.selectedHeatmapItem
                    scenariosModel:    state.scenariosModel
                    dependenciesModel: state.dependenciesModel
                    intakeItemsModel:  state.intakeModel
                    recentActionsModel: state.recentActionsModel
                }
            }
        }
    }
}
