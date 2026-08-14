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
import "tabs" as Tabs

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

    // ── Detail-page context actions ────────────────────────────────────
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

                AppWidgets.DetailTabBar {
                    id: primaryTabBar
                    Layout.fillWidth: true
                    tabs: state.tabLabels
                    currentIndex: state.activeTabIndex
                    onTabSelected: function(index) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setActiveTab(state.tabKeys[index])
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: state.activeTabIndex

                    Tabs.ExecutiveTab {
                        overviewModel:      root.overviewModel
                        topAtRiskModel:     state.topAtRiskModel
                        recentActionsModel: state.recentActionsModel
                    }

                    Tabs.HeatmapTab {
                        workspaceController: root.workspaceController
                        heatmapModel:        state.heatmapModel
                        heatmapColumns:      state.heatmapColumns
                        selectedRowId:       state.selectedRowId
                        onRowActivated: function(rowId) {
                            state.selectedRowId = rowId
                            state.pendingDetailSection = 0
                            state.detailOpen = true
                        }
                    }

                    Tabs.IntakeTab {
                        workspaceController:        root.workspaceController
                        intakeModel:                state.intakeModel
                        intakeStatusOptions:        root.workspaceController ? (root.workspaceController.intakeStatusOptions || []) : []
                        selectedIntakeStatusFilter: root.workspaceController ? root.workspaceController.selectedIntakeStatusFilter : "all"
                        fundingColumns:             state.fundingColumns
                    }

                    Tabs.ScenariosTab {
                        workspaceController: root.workspaceController
                        scenariosModel:      state.scenariosModel
                        templatesModel:      state.templatesModel
                    }

                    Tabs.CapacityTab {
                        capacityPoolModel: state.capacityPoolModel
                    }

                    Tabs.DependenciesTab {
                        workspaceController: root.workspaceController
                        dependenciesModel:   state.dependenciesModel
                        riskColumns:         state.riskColumns
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
                Component.onCompleted: {
                    scrollToSection(state.pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    state.selectedHeatmapItem
                        ? String(state.selectedHeatmapItem.title || "Project Details")
                        : "Project Details"
                    subtitle: state.selectedHeatmapItem
                        ? String(state.selectedHeatmapItem.subtitle || "")
                        : ""
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    onBackRequested: state.detailOpen = false
                }

                AppWidgets.SectionScopedInlineMessage {
                    width:   parent ? parent.width : 0
                    requestedVisible: state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone:    "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.SectionScopedInlineMessage {
                    width:   parent ? parent.width : 0
                    requestedVisible: state.detailOpen
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
                    pmProjectContext:  root.pmCatalog ? root.pmCatalog.pmProjectContext : null
                }
            }
        }
    }
}
