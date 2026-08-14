pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import control.dialogs 1.0 as PlatformDialogs
import "detail" as Detail

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API ────────────────────────────────────────────────
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformControlWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.controlWorkspace
        : null

    // -- R2 external navigation (PlatformNavigation) ---------------
    // Lets PlatformWorkspace select which of Control's own tabs (Approvals/
    // Audit -- its own internal, legitimate section navigation, unchanged)
    // is initially active when arriving from the new unified nav. Nothing
    // about the tab bar itself changes.
    property alias activePanel: state.activePanel

    title:    root.workspaceController
        ? (root.workspaceController.overview.title || "Control")
        : "Control"
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // RBAC: gates Approve/Reject specifically -- the workspace's own
    // entry gate (in PlatformControlWorkspaceController._is_accessible)
    // also admits "approval.request"-only submitters, who should see the
    // request but not working-looking decision buttons that would 403.
    readonly property bool _canDecide: root.platformCatalog
        ? root.platformCatalog.hasPermission("approval.decide")
        : true

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy       : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading    : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    // ── State ─────────────────────────────────────────────────────
    ControlWorkspaceState {
        id: state
        workspaceController: root.workspaceController
    }

    // ── Shell layout ──────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.workspaceController ? (root.workspaceController.overview.metrics || []) : []
        }

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

        // ── Main content ──────────────────────────────────────────
        RowLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 0

            ColumnLayout {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                // Excluded from the RowLayout while a detail is open, so the
                // detail overlay (the other RowLayout child) gets the full
                // width instead of the row splitting space between both.
                visible: !state.detailOpen
                spacing: 0

                // ── Panel tab bar ─────────────────────────────────
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
                                { id: "approvals",     label: "Approvals",     count: state.queueCount },
                                { id: "audit",         label: "Audit",         count: state.feedCount  }
                            ]

                            delegate: Item {
                                id: _tab
                                required property var modelData
                                readonly property bool _active: state.activePanel === _tab.modelData.id

                                implicitWidth:  _tabRow.implicitWidth + 16
                                Layout.fillHeight: true

                                RowLayout {
                                    id: _tabRow
                                    anchors.centerIn: parent
                                    spacing: 4

                                    AppControls.Label {
                                        text:           _tab.modelData.label
                                        color:          _tab._active ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      _tab._active
                                    }
                                    AppControls.Label {
                                        visible:        _tab.modelData.count > 0
                                        text:           String(_tab.modelData.count)
                                        color:          _tab._active ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
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
                                        state.activePanel          = _tab.modelData.id
                                        state.selectedRowId        = ""
                                        state.approvalDetailOpen   = false
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
                    visible: state.activePanel === "approvals" && !state.detailOpen && root._err.length === 0
                    spacing: 0

                    AppWidgets.TableToolbar {
                        id: approvalToolbar
                        Layout.fillWidth:  true
                        searchPlaceholder: "Search approvals..."
                        showFilter:        true
                        showViews:         true
                        showRefresh:       true
                        isBusy:            root._busy
                        onSearchChanged:   function(text) { state.searchText = text }
                        onFilterClicked:   approvalFilterPopup.open()
                        onViewsClicked:    approvalViewsPopup.open()
                        onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        sourceModel:   root.workspaceController ? root.workspaceController.approvalQueueTableModel : null
                        columns:       state.queueColumns
                        selectedRowId: state.selectedRowId
                        emptyText:     root.workspaceController
                            ? (root.workspaceController.approvalQueue.emptyState || "No pending requests")
                            : "No pending requests"
                        loading: root._load
                        onRowSelected:  function(id) { state.selectedRowId = id }
                        onRowActivated: function(id) {
                            state.selectedRowId      = id
                            state.approvalDetailOpen = true
                        }
                    }

                }

                // ── Audit panel ───────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    visible: state.activePanel === "audit" && root._err.length === 0
                    spacing: 0

                    AppWidgets.TableToolbar {
                        id: auditToolbar
                        Layout.fillWidth: true
                        searchPlaceholder: "Search not available for audit"
                        showFilter:  true
                        showViews:   false
                        showRefresh: true
                        isBusy:      root._busy
                        onFilterClicked:    auditFilterPopup.open()
                        onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
                    }

                    Flickable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
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
                            items:     root.workspaceController ? (root.workspaceController.auditFeed.items || []) : []
                            emptyText: root.workspaceController
                                ? (root.workspaceController.auditFeed.emptyState || "No recent activity")
                                : "No recent activity"
                        }
                    }
                }

                // R6.5: friendlier fallback than the raw danger banner
                // when the active panel's underlying data call fails.
                AppWidgets.PermissionState {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root._err.length > 0
                    message: root._err
                }
            }

            // ── Approval detail overlay ───────────────────────────
            Item {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                visible: state.detailOpen

                Loader {
                    id: _approvalDetailLoader
                    anchors.fill: parent
                    z:            10
                    active:       state.detailOpen
                    visible:      state.detailOpen && status === Loader.Ready
                    asynchronous: true
                    sourceComponent: Component {
                        Detail.ControlApprovalDetailPage {
                            approval:        state.queueItem || ({})
                            canDecide:       root._canDecide
                            busy:            root._busy
                            errorMessage:    root._err
                            feedbackMessage: root._ok
                            onBackRequested: {
                                state.approvalDetailOpen = false
                                state.selectedRowId = ""
                            }
                            onApproveRequested: function(item) { decisionDialog.openForDecision("approve", item) }
                            onRejectRequested:  function(item) { decisionDialog.openForDecision("reject",  item) }
                        }
                    }
                }
            }
        }
    }

    // ── Approval filter popup ─────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: approvalFilterPopup
        anchorItem:   approvalToolbar.filterButtonItem
        implicitWidth: 320
        padding:      Theme.AppTheme.marginMd
        closePolicy:  Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.AppTheme.surfaceRaised; radius: Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider; border.width: 1
        }

        ColumnLayout {
            width: parent.width; spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                text: "Filter Approvals"; color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Status" }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: ["All", "Pending", "Approved", "Rejected"]
                    currentIndex: {
                        const v = (root.workspaceController ? root.workspaceController.approvalStatusFilter : "").toUpperCase()
                        if (v === "PENDING") return 1
                        if (v === "APPROVED") return 2
                        if (v === "REJECTED") return 3
                        return 0
                    }
                    onActivated: {
                        if (!root.workspaceController) return
                        const values = ["", "PENDING", "APPROVED", "REJECTED"]
                        root.workspaceController.setApprovalStatusFilter(values[currentIndex] || "")
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Module / Entity Type" }
                AppControls.TextField {
                    Layout.fillWidth: true
                    text: root.workspaceController ? root.workspaceController.approvalEntityTypeFilter : ""
                    placeholderText: "e.g. purchase_order"
                    onEditingFinished: {
                        if (root.workspaceController) root.workspaceController.setApprovalEntityTypeFilter(text)
                    }
                }
            }

            AppControls.SecondaryButton {
                Layout.alignment: Qt.AlignRight
                text: "Close"; onClicked: approvalFilterPopup.close()
            }
        }
    }

    // ── Audit filter popup ─────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: auditFilterPopup
        anchorItem:   auditToolbar.filterButtonItem
        implicitWidth: 320
        padding:      Theme.AppTheme.marginMd
        closePolicy:  Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.AppTheme.surfaceRaised; radius: Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider; border.width: 1
        }

        ColumnLayout {
            width: parent.width; spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                text: "Filter Audit"; color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Entity Type" }
                AppControls.TextField {
                    Layout.fillWidth: true
                    text: root.workspaceController ? root.workspaceController.auditEntityTypeFilter : ""
                    placeholderText: "e.g. project"
                    onEditingFinished: {
                        if (root.workspaceController) root.workspaceController.setAuditEntityTypeFilter(text)
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Operation" }
                AppControls.TextField {
                    Layout.fillWidth: true
                    text: root.workspaceController ? root.workspaceController.auditOperationFilter : ""
                    placeholderText: "e.g. update"
                    onEditingFinished: {
                        if (root.workspaceController) root.workspaceController.setAuditOperationFilter(text)
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Severity" }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: ["All", "Low", "Medium", "High", "Critical"]
                    currentIndex: {
                        const v = (root.workspaceController ? root.workspaceController.auditSeverityFilter : "").toLowerCase()
                        const options = ["", "low", "medium", "high", "critical"]
                        const idx = options.indexOf(v)
                        return idx >= 0 ? idx : 0
                    }
                    onActivated: {
                        if (!root.workspaceController) return
                        const values = ["", "low", "medium", "high", "critical"]
                        root.workspaceController.setAuditSeverityFilter(values[currentIndex] || "")
                    }
                }
            }

            AppControls.SecondaryButton {
                Layout.alignment: Qt.AlignRight
                text: "Close"; onClicked: auditFilterPopup.close()
            }
        }
    }

    // ── Approval views popup ──────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: approvalViewsPopup
        anchorItem:   approvalToolbar.viewsButtonItem
        implicitWidth: 220
        padding:      4
        closePolicy:  Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.AppTheme.surfaceRaised; radius: Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider; border.width: 1
        }

        Column {
            width: parent.width; spacing: 2

            Repeater {
                model: ["Pending Only", "Rejected", "Recent Decisions", "High Risk", "My Reviews"]

                delegate: Rectangle {
                    required property string modelData
                    width: parent.width; height: 34
                    radius: Theme.AppTheme.radiusMd
                    color:  _viewMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                    AppControls.Label {
                        anchors { left: parent.left; leftMargin: Theme.AppTheme.spacingMd; verticalCenter: parent.verticalCenter }
                        text:  modelData; color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize
                    }
                    MouseArea {
                        id: _viewMA; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor; onClicked: approvalViewsPopup.close()
                    }
                }
            }
        }
    }

    // ── Approval decision dialog ──────────────────────────────────
    PlatformDialogs.ApprovalDecisionDialog {
        id: decisionDialog
        onDecisionConfirmed: function(mode, requestId, note) {
            if (root.workspaceController === null) return
            if (mode === "reject") root.workspaceController.rejectRequestWithNote(requestId, note)
            else                   root.workspaceController.approveRequestWithNote(requestId, note)
            decisionDialog.close()
        }
    }
}
