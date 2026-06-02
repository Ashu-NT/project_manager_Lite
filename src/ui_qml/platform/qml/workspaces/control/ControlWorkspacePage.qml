import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs
import "detail" as Detail

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API ────────────────────────────────────────────────
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var workspaceModel: root.platformCatalog
        ? root.platformCatalog.workspace("platform.control")
        : ({
            "routeId": "platform.control",
            "title": "Control",
            "summary": ""
        })
    property PlatformControllers.PlatformControlWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.controlWorkspace
        : null

    function approvalItemById(itemId) {
        const items = root.workspaceController
            ? (root.workspaceController.approvalQueue.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    title:    root.workspaceController
        ? (root.workspaceController.overview.title || root.workspaceModel.title)
        : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // ── Internal state ────────────────────────────────────────────
    property string _selectedRowId: ""
    property string _searchText:    ""
    property string _activePanel:   "approvals"

    // ── Approval queue pagination ─────────────────────────────────
    property int _queuePageSize:    50
    property int _queueCurrentPage: 0

    readonly property int _queueTotalCount: root.workspaceController
        ? (root.workspaceController.approvalQueue.items || []).length : 0
    readonly property int _queuePageCount:  Math.max(1, Math.ceil(root._queueTotalCount / root._queuePageSize))
    readonly property var _queuePageRows: root.workspaceController
        ? (root.workspaceController.approvalQueue.items || []).slice(
            root._queueCurrentPage * root._queuePageSize,
            (root._queueCurrentPage + 1) * root._queuePageSize
          )
        : []

    property bool _approvalDetailOpen: false
    readonly property bool _detailOpen: root._approvalDetailOpen
        && root._activePanel === "approvals"

    readonly property var _queueItem: {
        const id = root._selectedRowId
        if (!id) return null
        const items = root.workspaceController
            ? (root.workspaceController.approvalQueue.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property int _queueCount: root.workspaceController
        ? (root.workspaceController.approvalQueue.items || []).length : 0
    readonly property int _feedCount:  root.workspaceController
        ? (root.workspaceController.auditFeed.items || []).length : 0

    readonly property var _queueColumns: [
        { key: "title",       label: "Request",       flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Submitted by",  flex: 2, minWidth: 120, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",        flex: 0, minWidth: 90,  sortable: false, visible: true,
          type: "status" },
        { key: "metaText",    label: "Module / Info", flex: 2, minWidth: 120, sortable: false, visible: true }
    ]

    // ── Shell layout ──────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Compact metrics strip ─────────────────────────────────
        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.workspaceController
                ? (root.workspaceController.overview.metrics || []) : []
        }

        // ── Inline state banners ──────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: (root._load || root._busy) && root._err.length === 0
            tone:    "info"
            message: root._busy ? "Saving changes..." : "Loading..."
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._err.length > 0
            tone:    "danger"
            message: root._err
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._ok.length > 0 && root._err.length === 0
            tone:    "success"
            message: root._ok
        }

        // ── Main content: center queue + right inspector ──────────
        RowLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 0

            // ── Center column ─────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                spacing: 0

                // ── Panel nav tab bar ─────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.AppTheme.toolbarHeight - 4
                    color:  Theme.AppTheme.surfaceRaised
                    z:      1

                    Rectangle {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        anchors.fill:       parent
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        spacing: 0

                        Repeater {
                            model: [
                                { id: "approvals",     label: "Approvals",     count: root._queueCount },
                                { id: "audit",         label: "Audit",         count: root._feedCount  },
                                { id: "escalations",   label: "Escalations",   count: 0                },
                                { id: "system_events", label: "System Events", count: 0                }
                            ]

                            delegate: Item {
                                id: _tab
                                required property var modelData
                                readonly property bool _active: root._activePanel === _tab.modelData.id

                                implicitWidth:  _tabRow.implicitWidth + 16
                                Layout.fillHeight: true

                                RowLayout {
                                    id: _tabRow
                                    anchors.centerIn: parent
                                    spacing: 4

                                    AppControls.Label {
                                        text:           _tab.modelData.label
                                        color:          _tab._active
                                            ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      _tab._active
                                    }
                                    AppControls.Label {
                                        visible:        _tab.modelData.count > 0
                                        text:           String(_tab.modelData.count)
                                        color:          _tab._active
                                            ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                }

                                Rectangle {
                                    visible: _tab._active
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 2
                                    color:  Theme.AppTheme.accent
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape:  Qt.PointingHandCursor
                                    onClicked: {
                                        root._activePanel          = _tab.modelData.id
                                        root._selectedRowId        = ""
                                        root._approvalDetailOpen   = false
                                    }
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }
                    }
                }

                // ── Approvals panel ───────────────────────────────
                ColumnLayout {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    visible: root._activePanel === "approvals" && !root._detailOpen
                    spacing: 0

                    AppWidgets.TableToolbar {
                        id: approvalToolbar
                        Layout.fillWidth:  true
                        searchPlaceholder: "Search approvals..."
                        showFilter:        true
                        showViews:         true
                        showRefresh:       true
                        isBusy:            root._busy
                        onSearchChanged:   function(text) { root._searchText = text }
                        onFilterClicked:   approvalFilterPopup.open()
                        onViewsClicked:    approvalViewsPopup.open()
                        onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        sourceModel:   root.workspaceController ? root.workspaceController.approvalQueueTableModel : null
                        columns:       root._queueColumns
                        selectedRowId: root._selectedRowId
                        emptyText:     root.workspaceController
                            ? (root.workspaceController.approvalQueue.emptyState || "No pending requests")
                            : "No pending requests"
                        loading: root._load
                        onRowSelected:  function(id) { root._selectedRowId = id }
                        onRowActivated: function(id) {
                            root._selectedRowId = id
                            root._approvalDetailOpen = true
                        }
                    }

                    AppWidgets.TablePaginationBar {
                        Layout.fillWidth: true
                        currentPage: root._queueCurrentPage + 1
                        pageSize: root._queuePageSize
                        totalItems: root._queueTotalCount

                        pageSizeOptions: [25, 50, 100]
                        busy: root._busy || root._load
                        onPageRequested: function(page) {
                            root._queueCurrentPage = Math.max(0, page - 1)
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._queuePageSize = pageSize
                            root._queueCurrentPage = 0
                        }
                        /*

                            AppControls.Label {
                                text: {
                                    if (root._queueTotalCount === 0) return "No requests"
                                    const s = root._queueCurrentPage * root._queuePageSize + 1
                                    const e = Math.min((root._queueCurrentPage + 1) * root._queuePageSize, root._queueTotalCount)
                                    return s + "–" + e + " of " + root._queueTotalCount
                                }
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            Item { Layout.fillWidth: true }

                            AppControls.Label {
                                text: "Per page:"
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            Repeater {
                                model: [25, 50, 100]
                                delegate: Rectangle {
                                    id: _aqPgSzBtn
                                    required property int modelData
                                    implicitWidth: 28; implicitHeight: 22; radius: 3
                                    color: root._queuePageSize === _aqPgSzBtn.modelData
                                        ? Theme.AppTheme.accent
                                        : _aqPgSzMA.containsMouse ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surface
                                    border.color: root._queuePageSize === _aqPgSzBtn.modelData
                                        ? Theme.AppTheme.accent : Theme.AppTheme.divider
                                    border.width: 1
                                    AppControls.Label {
                                        anchors.centerIn: parent
                                        text:  String(_aqPgSzBtn.modelData)
                                        color: root._queuePageSize === _aqPgSzBtn.modelData
                                            ? "white" : Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    MouseArea {
                                        id: _aqPgSzMA
                                        anchors.fill: parent; hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: { root._queuePageSize = _aqPgSzBtn.modelData; root._queueCurrentPage = 0 }
                                    }
                                }
                            }

                            Rectangle {
                                implicitWidth: 22; implicitHeight: 22; radius: 3
                                color: _aqPrevMA.containsMouse && root._queueCurrentPage > 0
                                    ? Theme.AppTheme.hoverSurface : "transparent"
                                border.color: Theme.AppTheme.divider; border.width: 1
                                AppIcons.AppIcon {
                                    anchors.centerIn: parent; name: "chevron_left"; size: 10
                                    iconColor: root._queueCurrentPage > 0
                                        ? Theme.AppTheme.textSecondary : Theme.AppTheme.divider
                                }
                                MouseArea {
                                    id: _aqPrevMA
                                    anchors.fill: parent; hoverEnabled: true
                                    enabled: root._queueCurrentPage > 0
                                    cursorShape: root._queueCurrentPage > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: root._queueCurrentPage -= 1
                                }
                            }

                            AppControls.Label {
                                text:  (root._queueCurrentPage + 1) + " / " + root._queuePageCount
                                color: Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            Rectangle {
                                implicitWidth: 22; implicitHeight: 22; radius: 3
                                color: _aqNextMA.containsMouse && root._queueCurrentPage < root._queuePageCount - 1
                                    ? Theme.AppTheme.hoverSurface : "transparent"
                                border.color: Theme.AppTheme.divider; border.width: 1
                                AppIcons.AppIcon {
                                    anchors.centerIn: parent; name: "chevron_right"; size: 10
                                    iconColor: root._queueCurrentPage < root._queuePageCount - 1
                                        ? Theme.AppTheme.textSecondary : Theme.AppTheme.divider
                                }
                                MouseArea {
                                    id: _aqNextMA
                                    anchors.fill: parent; hoverEnabled: true
                                    enabled: root._queueCurrentPage < root._queuePageCount - 1
                                    cursorShape: root._queueCurrentPage < root._queuePageCount - 1
                                        ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: root._queueCurrentPage += 1
                                }
                            }
                        */
                    }
                }

                // ── Audit panel ───────────────────────────────────
                Item {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    visible: root._activePanel === "audit"

                    Flickable {
                        anchors.fill:   parent
                        contentWidth:   width
                        contentHeight:  _activityFeed.implicitHeight + Theme.AppTheme.marginMd * 2
                        clip:           true
                        boundsBehavior: Flickable.StopAtBounds

                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        AppWidgets.ActivityFeed {
                            id: _activityFeed
                            anchors {
                                top:         parent.top
                                left:        parent.left
                                right:       parent.right
                                topMargin:   Theme.AppTheme.marginMd
                                leftMargin:  Theme.AppTheme.marginMd
                                rightMargin: Theme.AppTheme.marginMd
                            }
                            items:     root.workspaceController
                                ? (root.workspaceController.auditFeed.items || []) : []
                            emptyText: root.workspaceController
                                ? (root.workspaceController.auditFeed.emptyState || "No recent activity")
                                : "No recent activity"
                        }
                    }
                }

                // ── Escalations panel ─────────────────────────────
                ColumnLayout {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    visible: root._activePanel === "escalations"
                    spacing: 0

                    AppWidgets.TableToolbar {
                        Layout.fillWidth:  true
                        searchPlaceholder: "Search escalations..."
                        showRefresh:       true
                        isBusy:            root._busy
                        onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        rows:      []
                        columns:   [
                            { key: "title",       label: "Reference",   flex: 3, minWidth: 200, sortable: true,  visible: true },
                            { key: "subtitle",    label: "Type",        flex: 2, minWidth: 140, sortable: false, visible: true },
                            { key: "statusLabel", label: "Severity",    flex: 0, minWidth: 100, sortable: false, visible: true, type: "status" },
                            { key: "metaText",    label: "SLA / Age",   flex: 2, minWidth: 140, sortable: false, visible: true }
                        ]
                        emptyText: "No active escalations — all requests are within SLA"
                        loading:   root._load
                    }
                }

                // ── System Events panel ────────────────────────────
                ColumnLayout {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    visible: root._activePanel === "system_events"
                    spacing: 0

                    AppWidgets.TableToolbar {
                        Layout.fillWidth:  true
                        searchPlaceholder: "Search system events..."
                        showFilter:        true
                        showRefresh:       true
                        isBusy:            root._busy
                        onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        rows:      []
                        columns:   [
                            { key: "title",       label: "Event",       flex: 4, minWidth: 240, sortable: true,  visible: true },
                            { key: "subtitle",    label: "Source",      flex: 2, minWidth: 140, sortable: false, visible: true },
                            { key: "statusLabel", label: "Severity",    flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
                            { key: "metaText",    label: "Timestamp",   flex: 2, minWidth: 160, sortable: false, visible: true }
                        ]
                        emptyText: "No system events recorded in this session"
                        loading:   root._load
                    }
                }
            }

            // ── Approval detail page — full-area overlay (stacked list/detail) ──
            // NOTE: this Loader is in a ColumnLayout (fills width, no explicit height).
            // We use a sibling Item to capture the fill height correctly.
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root._detailOpen

                Loader {
                    id: _approvalDetailLoader
                    anchors.fill: parent
                    z: 10
                    active:       root._detailOpen
                    visible:      root._detailOpen && status === Loader.Ready
                    asynchronous: true
                    sourceComponent: Component {
                        Detail.ControlApprovalDetailPage {
                            approval:        root._queueItem || ({})
                            busy:            root._busy
                            errorMessage:    root._err
                            feedbackMessage: root._ok
                            onBackRequested: {
                                root._approvalDetailOpen = false
                                root._selectedRowId = ""
                            }
                            onApproveRequested: function(item) {
                                decisionDialog.openForDecision("approve", item)
                            }
                            onRejectRequested: function(item) {
                                decisionDialog.openForDecision("reject", item)
                            }
                        }
                    }
                }
            }

            // ── REMOVED: Right detail inspector (replaced by ControlApprovalDetailPage above) ──
            // Keeping this block stub to avoid compile errors from removed ColumnLayout children below.
            // -- dead code removed --
            Item {
                id: _detailPanel
                Layout.fillHeight: true
                Layout.preferredWidth: 0
                visible: false
                // ── Inspector header (REMOVED, kept as stubs to satisfy QML ID references) ──
            }
        }
    }

    // ── Filter popup ──────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: approvalFilterPopup
        anchorItem: approvalToolbar.filterButtonItem
        implicitWidth: 320
        padding:     Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color:        Theme.AppTheme.surfaceRaised
            radius:       Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        ColumnLayout {
            width:   parent.width
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                text:           "Filter Approvals"
                color:          Theme.AppTheme.textPrimary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold:      true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text:    "Status, module, and date filters will appear here."
                color:   Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.SecondaryButton {
                Layout.alignment: Qt.AlignRight
                text:     "Close"
                onClicked: approvalFilterPopup.close()
            }
        }
    }

    // ── Views popup ───────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: approvalViewsPopup
        anchorItem: approvalToolbar.viewsButtonItem
        implicitWidth: 220
        padding:     4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color:        Theme.AppTheme.surfaceRaised
            radius:       Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        Column {
            width:   parent.width
            spacing: 2

            Repeater {
                model: ["Pending Only", "Rejected", "Recent Decisions", "High Risk", "My Reviews"]

                delegate: Rectangle {
                    required property string modelData
                    required property int    index
                    width:  parent.width
                    height: 34
                    radius: Theme.AppTheme.radiusMd
                    color:  _viewMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                    AppControls.Label {
                        anchors {
                            left:           parent.left
                            leftMargin:     Theme.AppTheme.spacingMd
                            verticalCenter: parent.verticalCenter
                        }
                        text:           modelData
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }

                    MouseArea {
                        id: _viewMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape:  Qt.PointingHandCursor
                        onClicked:    approvalViewsPopup.close()
                    }
                }
            }
        }
    }

    // ── Approval decision dialog (wiring unchanged) ───────────────
    PlatformDialogs.ApprovalDecisionDialog {
        id: decisionDialog

        onDecisionConfirmed: function(mode, requestId, note) {
            if (root.workspaceController === null) return
            if (mode === "reject") {
                root.workspaceController.rejectRequestWithNote(requestId, note)
            } else {
                root.workspaceController.approveRequestWithNote(requestId, note)
            }
            decisionDialog.close()
        }
    }
}
