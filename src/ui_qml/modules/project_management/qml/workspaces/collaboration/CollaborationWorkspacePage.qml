pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "panels" as Panels
import "sections" as Sections
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property ShellContexts.ShellContext shellModel
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementCollaborationWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.collaborationWorkspace
        : null

    // ── Controller-bound models ───────────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({ "routeId": "project_management.collaboration", "title": "Collaboration", "summary": "Workflow inbox, operational communication, mentions, approvals, and activity feed." })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": root.workspaceModel.title, "subtitle": root.workspaceModel.summary, "metrics": [] })
    readonly property var contextModel: root.workspaceController
        ? root.workspaceController.context
        : ({ "projectOptions": [], "teamOptions": [], "periodOptions": [], "unreadOptions": [] })
    readonly property var panelTabsModel: root.workspaceController
        ? (root.workspaceController.panelTabs || [])
        : []

    // ── State (all mutable state + computation lives in CollaborationWorkspaceState) ──
    CollaborationWorkspaceState {
        id: state
        workspaceController: root.workspaceController
        shellModel: root.shellModel
    }

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    // ── Layout ────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        Sections.CollaborationToolbarSection {
            id: contextToolbar
            Layout.fillWidth: true
            contextModel: root.contextModel
            selectedProjectId: state.selectedProjectId
            selectedTeamId: state.selectedTeamId
            selectedPeriodKey: state.selectedPeriodKey
            selectedUnreadKey: state.selectedUnreadKey
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            onProjectChanged: function(value) { if (root.workspaceController) root.workspaceController.setSelectedProjectId(value) }
            onTeamChanged: function(value) { if (root.workspaceController) root.workspaceController.setSelectedTeamId(value) }
            onPeriodChanged: function(value) { if (root.workspaceController) root.workspaceController.setSelectedPeriodKey(value) }
            onUnreadChanged: function(value) { if (root.workspaceController) root.workspaceController.setSelectedUnreadKey(value) }
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onSettingsRequested: settingsPopup.open()
        }

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: root.workspaceController && root.workspaceController.isBusy
                ? "Updating collaboration workflows..."
                : "Loading collaboration workspace..."
            compact: true
            modal: false
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: !state._detailOpen
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: !state._detailOpen
                && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        // ── Tab strip ─────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingSm
                anchors.rightMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingXs

                Repeater {
                    model: root.panelTabsModel

                    delegate: Item {
                        id: delegateRoot
                        required property var modelData
                        width: _tabRow.implicitWidth + 18
                        height: parent.height

                        readonly property bool _active: String(modelData.id || "") === state.activePanelId

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.AppTheme.radiusSm
                            color: delegateRoot._active
                                ? Theme.AppTheme.navSelectedBackground
                                : (_tabHover.hovered ? Theme.AppTheme.hoverSurface : "transparent")
                        }

                        Row {
                            id: _tabRow
                            anchors.centerIn: parent
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                text: String(delegateRoot.modelData.label || "")
                                color: delegateRoot._active ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: delegateRoot._active
                            }

                            Rectangle {
                                visible: Number(delegateRoot.modelData.count || 0) > 0
                                width: _countLabel.implicitWidth + 10
                                height: 18
                                radius: 9
                                color: delegateRoot._active ? Theme.AppTheme.accent : Theme.AppTheme.surfaceOverlay

                                AppControls.Label {
                                    id: _countLabel
                                    anchors.centerIn: parent
                                    text: String(delegateRoot.modelData.count || 0)
                                    color: delegateRoot._active ? Theme.AppTheme.textOnAccent : Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }
                        }

                        HoverHandler { id: _tabHover }
                        TapHandler {
                            onTapped: state.activePanelId = String(delegateRoot.modelData.id || "inbox")
                        }
                    }
                }
            }
        }

        // ── Content area ──────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                anchors.fill: parent
                visible: !state._detailOpen || detailPageLoader.status !== Loader.Ready
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceRaised
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        title: state._selectedRowItem
                            ? String(state._selectedRowItem.title || "")
                            : String(state._currentPanelModel.title || "")
                        subtitle: state._selectedRowItem
                            ? String(state._selectedRowItem.subtitle || state._selectedRowItem.supportingText || "")
                            : String(state._currentPanelModel.subtitle || "")
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: state._currentContextActions
                        onActionTriggered: function(actionId) { state._handleCurrentAction(actionId) }
                    }

                    AppWidgets.TableToolbar {
                        id: panelToolbar
                        Layout.fillWidth: true
                        searchText: state._panelSearchText(state.activePanelId)
                        searchPlaceholder: {
                            if (state.activePanelId === "mentions") return "Search mentions..."
                            if (state.activePanelId === "approvals") return "Search approvals..."
                            if (state.activePanelId === "team_updates") return "Search team updates..."
                            if (state.activePanelId === "activity") return "Search activity..."
                            if (state.activePanelId === "audit") return "Search audit..."
                            return "Search inbox..."
                        }
                        showFilter: true
                        showViews: true
                        showCustomize: state.activePanelId !== "activity" && state.activePanelId !== "audit"
                        showExport: true
                        showRefresh: true
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                        onSearchChanged: function(text) { state._setPanelSearchText(state.activePanelId, text) }
                        onFilterClicked: {
                            panelFilterPopup.anchorItem = panelToolbar.filterButtonItem
                            panelFilterPopup.open()
                        }
                        onViewsClicked: {
                            panelViewsPopup.anchorItem = panelToolbar.viewsButtonItem
                            panelViewsPopup.open()
                        }
                        onCustomizeClicked: {
                            if (state.activePanelId !== "activity" && state.activePanelId !== "audit")
                                panelTable.openColumnCustomizer(panelToolbar.customizeButtonItem)
                        }
                        onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
                        onExportRequested: { if (root.workspaceController !== null) root.workspaceController.exportPanel(state.activePanelId) }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        AppWidgets.DataTable {
                            id: panelTable
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: paginationBar.top
                            visible: state.activePanelId !== "activity" && state.activePanelId !== "audit"
                            columns: state._currentTableColumns
                            sourceModel: root.workspaceController
                                ? (state.activePanelId === "mentions"      ? root.workspaceController.mentionsTableModel
                                   : state.activePanelId === "approvals"   ? root.workspaceController.approvalsTableModel
                                   : state.activePanelId === "team_updates" ? root.workspaceController.teamUpdatesTableModel
                                   : root.workspaceController.inboxTableModel)
                                : null
                            selectedRowId: state._selectedRowId
                            emptyText: state._currentPanelModel.emptyState || "No collaboration items are available."
                            loading: root.workspaceController ? root.workspaceController.isLoading : false
                            onRowSelected: function(rowId) { state._selectedRowId = rowId }
                            onRowActivated: function(rowId) { state._openRow(state.activePanelId, rowId) }
                        }

                        AppWidgets.TablePaginationBar {
                            id: paginationBar
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            visible: state.activePanelId !== "activity" && state.activePanelId !== "audit"
                            currentPage: state._effectiveTablePage
                            pageSize: state._currentTablePageSize
                            totalItems: state._currentTableTotalItems
                            busy: root.workspaceController
                                ? (root.workspaceController.isBusy || root.workspaceController.isLoading)
                                : false
                            onPageRequested: function(page) { state._setPanelPage(state.activePanelId, page) }
                            onPageSizeRequested: function(pageSize) { state._setPanelPageSize(state.activePanelId, pageSize) }
                        }

                        ScrollView {
                            anchors.fill: parent
                            visible: state.activePanelId === "activity" || state.activePanelId === "audit"
                            contentWidth: availableWidth
                            clip: true

                            ColumnLayout {
                                width: parent.width
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.ActivityFeed {
                                    Layout.fillWidth: true
                                    items: state.activePanelId === "activity"
                                        ? state._activityFeedItems
                                        : state._auditFeedItems
                                    emptyText: state._currentPanelModel.emptyState || "No collaboration activity is available."
                                    onItemActivated: function(itemData) {
                                        const st = itemData && itemData.state ? itemData.state : {}
                                        state._navigateRoute(String(st.routeId || ""))
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── Detail page ───────────────────────────────────────────────
            Loader {
                id: detailPageLoader
                anchors.fill: parent
                active: state._detailOpen
                visible: state._detailOpen && status === Loader.Ready
                asynchronous: true
                sourceComponent: Component {
                    AppWidgets.SectionDetailPage {
                        id: detailPage
                        anchors.fill: parent
                        open: true
                        title: state.selectedDetailModel.title || "Collaboration Item"
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                        showEdit: false
                        showDelete: false
                        sections: ["Overview", "Activity", "Related Items", "Audit"]
                        onBackRequested: state._handleDetailAction("back")

                        AppWidgets.ContextualActionToolbar {
                            detailPagePinned: true
                            width: parent ? parent.width : 0
                            showBack: true
                            title: state.selectedDetailModel.title || "Workflow Item"
                            subtitle: state.selectedDetailModel.statusLabel || state.selectedDetailModel.subtitle || ""
                            busy: root.workspaceController ? root.workspaceController.isBusy : false
                            actions: state._detailActions()
                            onBackRequested: state._handleDetailAction("back")
                            onActionTriggered: function(actionId) { state._handleDetailAction(actionId) }
                        }

                        AppWidgets.InlineMessage {
                            width: parent ? parent.width : 0
                            visible: state._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                            tone: "danger"
                            message: root.workspaceController ? root.workspaceController.errorMessage : ""
                        }
                        AppWidgets.InlineMessage {
                            width: parent ? parent.width : 0
                            visible: state._detailOpen
                                && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                            tone: "success"
                            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                        }

                        Panels.CollaborationDetailPanel {
                            width: parent ? parent.width : 0
                            detailModel: state.selectedDetailModel
                            relatedItemsTableModel: root.workspaceController ? root.workspaceController.relatedItemsTableModel : null
                            detailPage: detailPage
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                            onRelatedItemActivated: function(itemData) {
                                const st = itemData && itemData.state ? itemData.state : {}
                                state._navigateRoute(String(st.routeId || ""))
                            }
                            onActivityItemActivated: function(itemData) {
                                const st = itemData && itemData.state ? itemData.state : {}
                                state._navigateRoute(String(st.routeId || ""))
                            }
                            onAuditItemActivated: function(itemData) {
                                const st = itemData && itemData.state ? itemData.state : {}
                                state._navigateRoute(String(st.routeId || ""))
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Popups ────────────────────────────────────────────────────────────
    Components.CollaborationFilterPopup {
        id: panelFilterPopup
        onClearFiltersRequested: state._clearFilters()
    }

    Components.CollaborationViewsPopup {
        id: panelViewsPopup
        onViewSelected: function(panelId, unreadKey) {
            state.activePanelId = panelId
            if (root.workspaceController) root.workspaceController.setSelectedUnreadKey(unreadKey)
        }
    }

    Components.CollaborationSettingsPopup {
        id: settingsPopup
        anchorItem: contextToolbar.settingsButtonItem
    }
}
