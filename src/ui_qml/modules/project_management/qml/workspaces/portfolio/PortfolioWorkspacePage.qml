pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

AppLayouts.WorkspaceFrame {
    id: root

    // ── Controller wiring ──────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController:
        root.pmCatalog ? root.pmCatalog.portfolioWorkspace : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Portfolio", "subtitle": "", "metrics": [] })

    readonly property var _heatmapModel: root.workspaceController
        ? root.workspaceController.heatmap
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _intakeModel: root.workspaceController
        ? root.workspaceController.intakeItems
        : ({ "title": "", "subtitle": "", "emptyState": "No intake items.", "items": [] })

    readonly property var _dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({ "title": "", "subtitle": "", "emptyState": "No dependencies.", "items": [] })

    readonly property var _scenariosModel: root.workspaceController
        ? root.workspaceController.scenarios
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _templatesModel: root.workspaceController
        ? root.workspaceController.templates
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _evaluationModel: root.workspaceController
        ? root.workspaceController.evaluation
        : ({ "title": "Scenario Evaluation", "subtitle": "", "emptyState": "Select a scenario.", "fields": [] })

    readonly property var _comparisonModel: root.workspaceController
        ? root.workspaceController.comparison
        : ({ "title": "Scenario Comparison", "subtitle": "", "emptyState": "Select two scenarios.", "fields": [] })

    readonly property var _recentActionsModel: root.workspaceController
        ? root.workspaceController.recentActions
        : ({ "title": "", "subtitle": "", "emptyState": "No recent activity.", "items": [] })

    readonly property var _capacityPoolModel: root.workspaceController
        ? root.workspaceController.capacityPool
        : ({ "title": "Capacity Pool", "subtitle": "", "emptyState": "No capacity data available.", "items": [] })

    // ── Workspace metadata ─────────────────────────────────────────────
    title:    root.overviewModel.title    || "Portfolio"
    subtitle: root.overviewModel.subtitle || ""

    // ── Table state ────────────────────────────────────────────────────
    property string _searchText:        ""
    property string _selectedRowId:     ""
    property var    _selectedRowIds:    []
    property int    _currentPage:       1
    property int    _pageSize:          25
    property int    _bottomTab:         0
    property string _selectedFundingId: ""
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    // ── Selected heatmap item (for detail page) ────────────────────────
    readonly property var _selectedHeatmapItem: {
        const id = root._selectedRowId
        if (!id) return null
        const items = root._heatmapModel.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id || "") === id) {
                return items[i]
            }
        }
        return null
    }

    // ── Main table column definitions ─────────────────────────────────
    readonly property var _heatmapColumns: [
        { "key": "title",          "label": "Project",       "flex": 3, "minWidth": 180, "sortable": true  },
        { "key": "subtitle",       "label": "Status",        "flex": 1, "minWidth": 90                     },
        { "key": "statusLabel",    "label": "Pressure",      "flex": 1, "minWidth": 80,  "type": "status"  },
        { "key": "supportingText", "label": "Delivery",      "flex": 2, "minWidth": 160                    },
        { "key": "metaText",       "label": "Cost Variance", "flex": 1, "minWidth": 100                    }
    ]

    // ── All filtered heatmap rows (client-side search) ─────────────────
    readonly property var _heatmapAllRows: {
        const items = root._heatmapModel.items || []
        const text  = root._searchText.toLowerCase()
        return items
            .filter(function(item) {
                return !text || String(item.title || "").toLowerCase().indexOf(text) >= 0
            })
            .map(function(item) {
                return {
                    "id":       String(item.id           || ""),
                    "name":     String(item.title        || ""),
                    "status":   String(item.subtitle     || ""),
                    "pressure": String(item.statusLabel  || ""),
                    "details":  String(item.supportingText || ""),
                    "variance": String(item.metaText     || "")
                }
            })
    }

    readonly property int _heatmapTotal: root._heatmapAllRows.length

    // ── Paginated heatmap rows ─────────────────────────────────────────
    readonly property var _pagedHeatmapRows: {
        const start = (root._currentPage - 1) * root._pageSize
        return root._heatmapAllRows.slice(start, start + root._pageSize)
    }

    // ── Funding tab DataTable rows ─────────────────────────────────────
    readonly property var _fundingColumns: [
        { "key": "title",          "label": "Intake Item",       "flex": 3, "minWidth": 160, "sortable": true },
        { "key": "statusLabel",    "label": "Status",            "flex": 1, "minWidth": 90,  "type": "status" },
        { "key": "subtitle",       "label": "Sponsor",           "flex": 2, "minWidth": 120                   },
        { "key": "supportingText", "label": "Budget / Capacity", "flex": 2, "minWidth": 160                   },
        { "key": "metaText",       "label": "Score",             "flex": 1, "minWidth": 60                    }
    ]

    readonly property var _fundingRows: {
        return (root._intakeModel.items || []).map(function(item) {
            return {
                "id":      String(item.id          || ""),
                "title":   String(item.title       || ""),
                "status":  String(item.statusLabel || ""),
                "sponsor": String(item.subtitle    || "").replace("Sponsor: ", ""),
                "details": String(item.supportingText || ""),
                "score":   String(item.metaText    || "")
            }
        })
    }

    // ── Risks tab DataTable rows ───────────────────────────────────────
    readonly property var _riskColumns: [
        { "key": "title",          "label": "Dependency", "flex": 3, "minWidth": 200                   },
        { "key": "subtitle",       "label": "Type",        "flex": 1, "minWidth": 100                   },
        { "key": "statusLabel",    "label": "Pressure",    "flex": 1, "minWidth": 80, "type": "status"  },
        { "key": "supportingText", "label": "Status",      "flex": 2, "minWidth": 160                   }
    ]

    readonly property var _riskRows: {
        return (root._dependenciesModel.items || []).map(function(item) {
            return {
                "id":      String(item.id           || ""),
                "link":    String(item.title        || ""),
                "type":    String(item.subtitle     || ""),
                "status":  String(item.statusLabel  || ""),
                "details": String(item.supportingText || "")
            }
        })
    }

    // ── Activity feed items ────────────────────────────────────────────
    readonly property var _activityItems: {
        return (root._recentActionsModel.items || []).map(function(item) {
            return {
                "title":       String(item.title       || ""),
                "metaText":    String(item.metaText    || item.subtitle || ""),
                "statusLabel": String(item.statusLabel || "")
            }
        })
    }

    // ── Detail page contextual actions ─────────────────────────────────
    readonly property var _detailActions: {
        const idx = detailPage ? detailPage.activeSectionIndex : 0
        if (idx === 0) {
            return [
                { "id": "evaluate", "label": "Evaluate", "icon": "approve",
                  "enabled": true, "danger": false }
            ]
        }
        return []
    }

    // ── Helpers ────────────────────────────────────────────────────────
    function _optionIndexForValue(options, value) {
        const opts = options || []
        for (let i = 0; i < opts.length; i += 1) {
            if (String(opts[i].value || "") === String(value || "")) {
                return i
            }
        }
        return 0
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
            visible: !root._detailOpen

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                // State banners
                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    loading: root.workspaceController
                        ? root.workspaceController.isBusy
                            && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    message: "Saving changes..."
                    compact: true
                    modal:   false
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !root._detailOpen
                        && String(root.workspaceController
                        ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !root._detailOpen
                        && String(root.workspaceController
                        ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController
                        ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                // Governance toolbar
                PortfolioGovernanceToolbar {
                    Layout.fillWidth: true
                    scenarioOptions: root.workspaceController
                        ? (root.workspaceController.scenarioOptions || []) : []
                    selectedScenarioId: root.workspaceController
                        ? root.workspaceController.selectedScenarioId : ""
                    selectedBaseScenarioId: root.workspaceController
                        ? root.workspaceController.selectedBaseScenarioId : ""
                    selectedCompareScenarioId: root.workspaceController
                        ? root.workspaceController.selectedCompareScenarioId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onScenarioSelected: function(id) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectScenario(id)
                        }
                    }
                    onCompareBaseSelected: function(id) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectCompareBase(id)
                        }
                    }
                    onCompareScenarioSelected: function(id) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectCompareScenario(id)
                        }
                    }
                    onRefreshRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }
                    onCompareRequested: { root._bottomTab = 2 }
                    onRebalanceRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.exportPortfolio()
                        }
                    }
                }

                // Executive KPI strip
                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                // Table toolbar
                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchText:        root._searchText
                    searchPlaceholder: "Search portfolio projects..."
                    showRefresh: true
                    showExport:  true
                    showFilter:  true
                    showCreate:  false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        root._searchText = text
                        root._currentPage = 1
                        root._selectedRowIds = []
                    }
                    onFilterClicked: filterPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.exportPortfolio()
                        }
                    }
                }

                // ── Content area ───────────────────────────────────────
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    // Main heatmap DataTable
                    AppWidgets.DataTable {
                        id: _heatmapTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._heatmapColumns
                        sourceModel: root.workspaceController ? root.workspaceController.heatmapTableModel : null
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root._heatmapModel.emptyState
                            || "No portfolio projects available."
                        selectedRowId:  root._selectedRowId
                        selectedRowIds: root._selectedRowIds

                        onRowSelected: function(rowId) {
                            root._selectedRowId = rowId
                        }
                        onRowActivated: function(rowId) {
                            root._selectedRowId = rowId
                            root._pendingDetailSection = 0
                            root._detailOpen = true
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            const ids = root._selectedRowIds.slice()
                            const idx = ids.indexOf(rowId)
                            if (selected && idx < 0) {
                                ids.push(rowId)
                            } else if (!selected && idx >= 0) {
                                ids.splice(idx, 1)
                            }
                            root._selectedRowIds = ids
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (allSelected) {
                                root._selectedRowIds = root._pagedHeatmapRows.map(
                                    function(r) { return String(r.id || "") }
                                )
                            } else {
                                root._selectedRowIds = []
                            }
                        }
                    }

                    // Pagination bar (sits on top of bottom panel)
                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _bottomPanel.top
                        currentPage:  root._currentPage
                        pageSize:     root._pageSize
                        totalItems:   root._heatmapTotal
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) { root._currentPage = page }
                        onPageSizeRequested: function(ps) {
                            root._pageSize = ps
                            root._currentPage = 1
                        }
                    }

                    // Bulk action bar
                    AppWidgets.BulkActionBar {
                        id: _bulkBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root._selectedRowIds.length
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "evaluate", "label": "Evaluate Scenario",
                              "icon": "approve", "danger": false, "enabled": true }
                        ]

                        onCancelRequested: { root._selectedRowIds = [] }
                        onActionTriggered: function(actionId) {
                            if (actionId === "evaluate") {
                                root._bottomTab = 2
                            }
                        }
                    }

                    // Filter popup
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem: tableToolbar.filterButtonItem
                        width: 280
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Intake Status"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController
                                    ? (root.workspaceController.intakeStatusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController
                                    ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController
                                        ? (root.workspaceController.intakeStatusOptions || []) : [],
                                    root.workspaceController
                                        ? root.workspaceController.selectedIntakeStatusFilter : "all"
                                )
                                onActivated: function(idx) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.intakeStatusOptions || []) : []
                                    if (root.workspaceController !== null && opts[idx]) {
                                        root.workspaceController.setIntakeStatusFilter(
                                            String(opts[idx].value || "all")
                                        )
                                    }
                                }
                            }

                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Clear Filters"
                                iconName: "delete"
                                enabled: !(root.workspaceController
                                    ? root.workspaceController.isBusy : false)
                                onClicked: {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.setIntakeStatusFilter("all")
                                    }
                                    filterPopup.close()
                                }
                            }
                        }
                    }

                    // ── Bottom tabbed panel ────────────────────────────
                    Rectangle {
                        id: _bottomPanel
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        height: 268
                        color: Theme.AppTheme.surfaceRaised
                        radius: Theme.AppTheme.radiusMd
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            // Tab strip
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 36
                                color: Theme.AppTheme.surfaceAlt
                                radius: Theme.AppTheme.radiusMd

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin:  Theme.AppTheme.marginMd
                                    anchors.rightMargin: Theme.AppTheme.marginMd
                                    spacing: Theme.AppTheme.spacingXs

                                    Repeater {
                                        model: ["Funding", "Risks", "Capacity", "Governance", "Activity"]

                                        delegate: Rectangle {
                                            id: _tabBtn
                                            required property var modelData
                                            required property int index

                                            implicitWidth:  _tabLabel.implicitWidth + 20
                                            implicitHeight: 26
                                            radius: Theme.AppTheme.radiusSm
                                            color: root._bottomTab === _tabBtn.index
                                                ? Theme.AppTheme.accent
                                                : (_tabHover.containsMouse
                                                    ? Theme.AppTheme.hoverSurface
                                                    : Qt.rgba(0, 0, 0, 0))

                                            AppControls.Label {
                                                id: _tabLabel
                                                anchors.centerIn: parent
                                                text: String(_tabBtn.modelData || "")
                                                color: root._bottomTab === _tabBtn.index
                                                    ? "white"
                                                    : Theme.AppTheme.textSecondary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                font.bold: root._bottomTab === _tabBtn.index
                                            }

                                            MouseArea {
                                                id: _tabHover
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: root._bottomTab = _tabBtn.index
                                            }
                                        }
                                    }

                                    Item { Layout.fillWidth: true }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: Theme.AppTheme.divider
                            }

                            // Tab content
                            StackLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                currentIndex: root._bottomTab

                                // ── Tab 0: Funding ─────────────────────
                                Item {
                                    ColumnLayout {
                                        anchors.fill: parent
                                        spacing: 0

                                        AppWidgets.DataTable {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            columns:  root._fundingColumns
                                            sourceModel: root.workspaceController ? root.workspaceController.intakeItemsTableModel : null
                                            emptyText: root._intakeModel.emptyState
                                                || "No intake items available."
                                            multiSelect: false
                                            selectedRowId: root._selectedFundingId

                                            onRowSelected: function(rowId) {
                                                root._selectedFundingId = rowId
                                            }
                                            onRowActivated: function(rowId) {
                                                root._selectedFundingId = rowId
                                            }
                                        }

                                        // Inline action bar for selected intake item
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 40
                                            visible: root._selectedFundingId.length > 0
                                            color: Theme.AppTheme.surfaceAlt

                                            Rectangle {
                                                anchors.top:   parent.top
                                                anchors.left:  parent.left
                                                anchors.right: parent.right
                                                height: 1
                                                color: Theme.AppTheme.divider
                                            }

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin:  Theme.AppTheme.marginMd
                                                anchors.rightMargin: Theme.AppTheme.marginMd
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    text: "Status:"
                                                    color: Theme.AppTheme.textMuted
                                                    font.family: Theme.AppTheme.fontFamily
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                }

                                                AppControls.SecondaryButton {
                                                    text: "Approve"
                                                    iconName: "approve"
                                                    enabled: !(root.workspaceController
                                                        ? root.workspaceController.isBusy : false)
                                                    onClicked: {
                                                        if (root.workspaceController !== null) {
                                                            root.workspaceController.updateIntakeItemStatus(
                                                                root._selectedFundingId, "APPROVED"
                                                            )
                                                            root._selectedFundingId = ""
                                                        }
                                                    }
                                                }

                                                AppControls.SecondaryButton {
                                                    text: "Review"
                                                    iconName: "edit"
                                                    enabled: !(root.workspaceController
                                                        ? root.workspaceController.isBusy : false)
                                                    onClicked: {
                                                        if (root.workspaceController !== null) {
                                                            root.workspaceController.updateIntakeItemStatus(
                                                                root._selectedFundingId, "REVIEW"
                                                            )
                                                            root._selectedFundingId = ""
                                                        }
                                                    }
                                                }

                                                AppControls.SecondaryButton {
                                                    text: "Reject"
                                                    iconName: "delete"
                                                    enabled: !(root.workspaceController
                                                        ? root.workspaceController.isBusy : false)
                                                    onClicked: {
                                                        if (root.workspaceController !== null) {
                                                            root.workspaceController.updateIntakeItemStatus(
                                                                root._selectedFundingId, "REJECTED"
                                                            )
                                                            root._selectedFundingId = ""
                                                        }
                                                    }
                                                }

                                                Item { Layout.fillWidth: true }

                                                AppControls.SecondaryButton {
                                                    text: "Clear"
                                                    onClicked: { root._selectedFundingId = "" }
                                                }
                                            }
                                        }
                                    }
                                }

                                // ── Tab 1: Risks ───────────────────────
                                Item {
                                    AppWidgets.DataTable {
                                        anchors.fill: parent
                                        columns:  root._riskColumns
                                        sourceModel: root.workspaceController ? root.workspaceController.portfolioDependenciesTableModel : null
                                        emptyText: root._dependenciesModel.emptyState
                                            || "No cross-project dependencies recorded."
                                        onRowSelected: function(rowId) {}
                                    }
                                }

                                // ── Tab 2: Capacity ────────────────────
                                Item {
                                    Flickable {
                                        anchors.fill: parent
                                        contentWidth: width
                                        contentHeight: _capCol.implicitHeight
                                            + Theme.AppTheme.marginMd * 2
                                        clip: true

                                        ColumnLayout {
                                            id: _capCol
                                            anchors.left:        parent.left
                                            anchors.right:       parent.right
                                            anchors.top:         parent.top
                                            anchors.leftMargin:  Theme.AppTheme.marginMd
                                            anchors.rightMargin: Theme.AppTheme.marginMd
                                            anchors.topMargin:   Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingMd

                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                text: root._capacityPoolModel.title || "Capacity Pool"
                                                color: Theme.AppTheme.textPrimary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                font.bold: true
                                            }
                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                text: root._capacityPoolModel.subtitle || ""
                                                color: Theme.AppTheme.textMuted
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.captionSize
                                                wrapMode: Text.Wrap
                                                visible: !!text
                                            }

                                            AppWidgets.EmptyState {
                                                Layout.fillWidth: true
                                                visible: (root._capacityPoolModel.items || []).length === 0
                                                title: "No capacity data"
                                                message: root._capacityPoolModel.emptyState
                                                    || "Assign resources to tasks to see portfolio-level capacity demand."
                                            }

                                            Repeater {
                                                model: root._capacityPoolModel.items || []
                                                delegate: Rectangle {
                                                    id: _capRow
                                                    required property var modelData
                                                    required property int index
                                                    Layout.fillWidth: true
                                                    implicitHeight: _capRowContent.implicitHeight + Theme.AppTheme.spacingSm * 2
                                                    color: (_capRow.modelData.state && _capRow.modelData.state.overloaded)
                                                        ? Qt.rgba(Theme.AppTheme.danger.r, Theme.AppTheme.danger.g, Theme.AppTheme.danger.b, 0.08)
                                                        : Theme.AppTheme.surfaceAlt
                                                    radius: Theme.AppTheme.radiusSm

                                                    RowLayout {
                                                        id: _capRowContent
                                                        anchors.left: parent.left
                                                        anchors.right: parent.right
                                                        anchors.top: parent.top
                                                        anchors.margins: Theme.AppTheme.spacingSm
                                                        spacing: Theme.AppTheme.spacingSm

                                                        AppControls.Label {
                                                            Layout.fillWidth: true
                                                            text: String(_capRow.modelData.title || "")
                                                            color: Theme.AppTheme.textPrimary
                                                            font.family: Theme.AppTheme.fontFamily
                                                            font.pixelSize: Theme.AppTheme.smallSize
                                                            elide: Text.ElideRight
                                                        }
                                                        AppControls.Label {
                                                            text: String(_capRow.modelData.subtitle || "")
                                                            color: Theme.AppTheme.textMuted
                                                            font.family: Theme.AppTheme.fontFamily
                                                            font.pixelSize: Theme.AppTheme.captionSize
                                                        }
                                                        AppControls.Label {
                                                            text: String(_capRow.modelData.statusLabel || "")
                                                            color: (_capRow.modelData.state && _capRow.modelData.state.overloaded)
                                                                ? Theme.AppTheme.danger
                                                                : Theme.AppTheme.success
                                                            font.family: Theme.AppTheme.fontFamily
                                                            font.pixelSize: Theme.AppTheme.smallSize
                                                            font.bold: true
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // ── Tab 3: Governance ──────────────────
                                Item {
                                    Flickable {
                                        anchors.fill: parent
                                        contentWidth: width
                                        contentHeight: _govCol.implicitHeight
                                            + Theme.AppTheme.marginMd * 2
                                        clip: true

                                        ColumnLayout {
                                            id: _govCol
                                            anchors.left:        parent.left
                                            anchors.right:       parent.right
                                            anchors.top:         parent.top
                                            anchors.leftMargin:  Theme.AppTheme.marginMd
                                            anchors.rightMargin: Theme.AppTheme.marginMd
                                            anchors.topMargin:   Theme.AppTheme.spacingSm
                                            spacing: Theme.AppTheme.spacingSm

                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                text: root._templatesModel.title || "Scoring Templates"
                                                color: Theme.AppTheme.textSecondary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.captionSize
                                                font.bold: true
                                            }

                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                text: root._templatesModel.subtitle || ""
                                                visible: text.length > 0
                                                color: Theme.AppTheme.textMuted
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                wrapMode: Text.WordWrap
                                            }

                                            Repeater {
                                                model: root._templatesModel.items || []

                                                delegate: Rectangle {
                                                    id: _tplRow
                                                    required property var modelData

                                                    Layout.fillWidth: true
                                                    height: _tplRowLayout.implicitHeight + 16
                                                    radius: Theme.AppTheme.radiusSm
                                                    color: Theme.AppTheme.surfaceAlt
                                                    border.color: Theme.AppTheme.subtleBorder
                                                    border.width: 1

                                                    RowLayout {
                                                        id: _tplRowLayout
                                                        anchors.left:    parent.left
                                                        anchors.right:   parent.right
                                                        anchors.top:     parent.top
                                                        anchors.margins: 8
                                                        spacing: Theme.AppTheme.spacingSm

                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            spacing: 2

                                                            AppControls.Label {
                                                                Layout.fillWidth: true
                                                                text: String(_tplRow.modelData.title || "")
                                                                color: Theme.AppTheme.textPrimary
                                                                font.family: Theme.AppTheme.fontFamily
                                                                font.pixelSize: Theme.AppTheme.smallSize
                                                                font.bold: true
                                                                elide: Text.ElideRight
                                                            }

                                                            AppControls.Label {
                                                                Layout.fillWidth: true
                                                                text: String(_tplRow.modelData.subtitle || "")
                                                                color: Theme.AppTheme.textSecondary
                                                                font.family: Theme.AppTheme.fontFamily
                                                                font.pixelSize: Theme.AppTheme.captionSize
                                                                elide: Text.ElideRight
                                                            }
                                                        }

                                                        AppWidgets.StatusChip {
                                                            status: String(_tplRow.modelData.statusLabel || "")
                                                        }

                                                        AppControls.SecondaryButton {
                                                            visible: Boolean(_tplRow.modelData.canPrimaryAction)
                                                            text: "Activate"
                                                            iconName: "approve"
                                                            enabled: !(root.workspaceController
                                                                ? root.workspaceController.isBusy : false)
                                                            onClicked: {
                                                                if (root.workspaceController !== null) {
                                                                    root.workspaceController.activateTemplate(
                                                                        String(
                                                                            (_tplRow.modelData.state || {})
                                                                            .templateId || ""
                                                                        )
                                                                    )
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                visible: (root._templatesModel.items || []).length === 0
                                                text: root._templatesModel.emptyState
                                                    || "No scoring templates available."
                                                color: Theme.AppTheme.textMuted
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }
                                }

                                // ── Tab 4: Activity ────────────────────
                                Item {
                                    AppWidgets.ActivityFeed {
                                        anchors.fill: parent
                                        anchors.margins: Theme.AppTheme.marginMd
                                        items: root._activityItems
                                        emptyText: root._recentActionsModel.emptyState
                                            || "No recent portfolio activity."
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Full loading overlay over list page ───────────────────────
        AppWidgets.LoadingOverlay {
            anchors.fill: _listPage
            z: 15
            loading: _listPage.visible
                && (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading portfolio data..."
        }

        // ── Detail page (covers full area, z:20) ──────────────────────
        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active: root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: [
                    "Overview",
                    "Scenarios",
                    "Dependencies",
                    "Funding",
                    "Activity"
                ]
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root._selectedHeatmapItem
                        ? String(root._selectedHeatmapItem.title || "Project Details")
                        : "Project Details"
                    subtitle: root._selectedHeatmapItem
                        ? String(root._selectedHeatmapItem.subtitle || "")
                        : ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "evaluate") {
                            root._detailOpen = false
                            root._bottomTab = 2
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                PortfolioDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    heatmapItem: root._selectedHeatmapItem
                    scenariosModel: root._scenariosModel
                    dependenciesModel: root._dependenciesModel
                    intakeItemsModel: root._intakeModel
                    recentActionsModel: root._recentActionsModel
                }
            }
        }
    }
}
