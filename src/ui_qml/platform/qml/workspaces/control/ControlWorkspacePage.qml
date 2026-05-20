import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API (backward-compatible) ─────────────────────────
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

    readonly property bool _detailOpen: root._selectedRowId.length > 0

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

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy           : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading        : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage     : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage  : ""

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

        // ── Main content: queue (center) + detail (right) ─────────
        RowLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 0

            // ── Center column: queue table + audit feed ───────────
            ColumnLayout {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                spacing: 0

                // ── Approval Queue toolbar ────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.AppTheme.toolbarHeight - 6
                    color:  Theme.AppTheme.surfaceRaised
                    z:      1

                    Rectangle {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        anchors.fill:        parent
                        anchors.leftMargin:  Theme.AppTheme.marginMd
                        anchors.rightMargin: 8
                        spacing:             Theme.AppTheme.spacingXs

                        Label {
                            text:           "Approval Queue"
                            color:          Theme.AppTheme.textPrimary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold:      true
                        }

                        Label {
                            visible:        root._queueCount > 0
                            text:           String(root._queueCount)
                            color:          Theme.AppTheme.textMuted
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            leftPadding:    4
                        }

                        Item { Layout.fillWidth: true }

                        Rectangle {
                            width: 26; height: 26; radius: 4
                            color: _refreshMA.containsMouse
                                ? Theme.AppTheme.hoverSurface : "transparent"

                            AppIcons.AppIcon {
                                anchors.centerIn: parent
                                name: "refresh"; size: 12
                                iconColor: Theme.AppTheme.textMuted
                            }

                            MouseArea {
                                id: _refreshMA
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape:  Qt.PointingHandCursor
                                enabled:      !root._busy
                                onClicked: {
                                    if (root.workspaceController) root.workspaceController.refresh()
                                }
                            }
                        }
                    }
                }

                // ── Contextual action toolbar — visible when request selected ─
                AppWidgets.ContextualActionToolbar {
                    Layout.fillWidth: true
                    visible:  root._selectedRowId.length > 0
                    title:    root._queueItem ? (root._queueItem.title || "") : ""
                    subtitle: root._queueItem ? (root._queueItem.statusLabel || "") : ""
                    busy:     root._busy
                    actions: [
                        { id: "approve", label: "Approve", icon: "approve", enabled: true,  danger: false },
                        { id: "reject",  label: "Reject",  icon: "reject",  enabled: true,  danger: true  }
                    ]
                    onActionTriggered: function(id) {
                        const item = root._queueItem
                        if (item === null) return
                        if (id === "approve") decisionDialog.openForDecision("approve", item)
                        else if (id === "reject") decisionDialog.openForDecision("reject", item)
                    }
                }

                // ── Approval Queue DataTable (fills center) ───────
                AppWidgets.DataTable {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true

                    rows:          root.workspaceController
                        ? (root.workspaceController.approvalQueue.items || []) : []
                    columns:       root._queueColumns
                    selectedRowId: root._selectedRowId
                    emptyText:     root.workspaceController
                        ? (root.workspaceController.approvalQueue.emptyState || "No pending requests")
                        : "No pending requests"
                    loading: root._load

                    onRowSelected: function(id) {
                        root._selectedRowId = id
                    }
                    onRowActivated: function(id) {
                        root._selectedRowId = id
                        const item = root.approvalItemById(id)
                        if (item !== null) decisionDialog.openForDecision("approve", item)
                    }
                }

                // ── Audit Feed header ─────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.AppTheme.toolbarHeight - 6
                    color:  Theme.AppTheme.surfaceRaised

                    Rectangle {
                        anchors { top: parent.top; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }
                    Rectangle {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        anchors.fill:        parent
                        anchors.leftMargin:  Theme.AppTheme.marginMd
                        anchors.rightMargin: 8
                        spacing:             Theme.AppTheme.spacingXs

                        Label {
                            text: root.workspaceController
                                ? (root.workspaceController.auditFeed.title || "Recent Activity")
                                : "Recent Activity"
                            color:          Theme.AppTheme.textPrimary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold:      true
                        }

                        Label {
                            visible:        root._feedCount > 0
                            text:           String(root._feedCount)
                            color:          Theme.AppTheme.textMuted
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            leftPadding:    4
                        }

                        Item { Layout.fillWidth: true }
                    }
                }

                // ── Audit Feed compact list ────────────────────────
                Item {
                    Layout.fillWidth:       true
                    Layout.preferredHeight: 160

                    ListView {
                        id: _feedList
                        anchors.fill:   parent
                        clip:           true
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.workspaceController
                            ? (root.workspaceController.auditFeed.items || []) : []

                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: Rectangle {
                            required property var modelData
                            required property int index

                            width:  _feedList.width
                            height: 32
                            color:  _feedRowMA.containsMouse
                                ? Theme.AppTheme.hoverSurface : "transparent"

                            Rectangle {
                                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                height: 1; color: Theme.AppTheme.divider
                            }

                            RowLayout {
                                anchors.fill:        parent
                                anchors.leftMargin:  Theme.AppTheme.marginMd
                                anchors.rightMargin: Theme.AppTheme.marginSm
                                spacing:             Theme.AppTheme.spacingSm

                                Label {
                                    Layout.fillWidth: true
                                    text:           modelData.title || ""
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    elide:          Text.ElideRight
                                }

                                AppWidgets.StatusChip {
                                    visible: (modelData.statusLabel || "").length > 0
                                    status:  modelData.statusLabel || ""
                                }

                                Label {
                                    visible: (modelData.metaText || "").length > 0
                                    text:    modelData.metaText || ""
                                    color:   Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide:          Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: _feedRowMA
                                anchors.fill: parent
                                hoverEnabled: true
                            }
                        }
                    }

                    AppWidgets.EmptyState {
                        anchors.centerIn: parent
                        width:   Math.min(_feedList.width, 240)
                        visible: _feedList.count === 0 && !root._load
                        title:   root.workspaceController
                            ? (root.workspaceController.auditFeed.emptyState || "No recent activity")
                            : "No recent activity"
                    }
                }
            }

            // ── Right contextual detail panel ─────────────────────
            Rectangle {
                id: _detailPanel
                Layout.fillHeight:     true
                Layout.preferredWidth: 288
                visible:               root._detailOpen
                color:                 Theme.AppTheme.surface
                z:                     1

                Rectangle {
                    anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                    width: 1; color: Theme.AppTheme.divider
                }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Panel header — ContextualActionToolbar for request actions
                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        showBack: true
                        title:    "Request Detail"
                        subtitle: root._queueItem ? (root._queueItem.statusLabel || "") : ""
                        busy:     root._busy
                        actions: [
                            { id: "approve", label: "Approve", icon: "approve", enabled: true, danger: false },
                            { id: "reject",  label: "Reject",  icon: "reject",  enabled: true, danger: true  }
                        ]
                        onBackRequested: root._selectedRowId = ""
                        onActionTriggered: function(id) {
                            const item = root._queueItem
                            if (item === null) return
                            if (id === "approve") decisionDialog.openForDecision("approve", item)
                            else if (id === "reject") decisionDialog.openForDecision("reject", item)
                        }
                    }

                    // Panel content (scrollable)
                    Flickable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        contentWidth:      width
                        contentHeight:     _panelContent.implicitHeight
                        clip:              true
                        boundsBehavior:    Flickable.StopAtBounds

                        ColumnLayout {
                            id: _panelContent
                            width:   parent.width
                            spacing: Theme.AppTheme.spacingSm

                            // Request title
                            Label {
                                Layout.fillWidth:   true
                                Layout.leftMargin:  Theme.AppTheme.marginMd
                                Layout.rightMargin: Theme.AppTheme.marginMd
                                Layout.topMargin:   Theme.AppTheme.marginMd
                                text:           root._queueItem ? (root._queueItem.title || "") : ""
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold:      true
                                wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                            }

                            // Status chip
                            AppWidgets.StatusChip {
                                Layout.leftMargin: Theme.AppTheme.marginMd
                                visible: root._queueItem
                                    ? (root._queueItem.statusLabel || "").length > 0 : false
                                status: root._queueItem
                                    ? (root._queueItem.statusLabel || "") : ""
                            }

                            Rectangle {
                                Layout.fillWidth:   true
                                Layout.leftMargin:  Theme.AppTheme.marginMd
                                Layout.rightMargin: Theme.AppTheme.marginMd
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // Submitted by
                            ColumnLayout {
                                Layout.fillWidth:   true
                                Layout.leftMargin:  Theme.AppTheme.marginMd
                                Layout.rightMargin: Theme.AppTheme.marginMd
                                spacing: 2
                                visible: root._queueItem
                                    ? (root._queueItem.subtitle || "").length > 0 : false

                                Label {
                                    text:           "Submitted by"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text:           root._queueItem
                                        ? (root._queueItem.subtitle || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Module / info
                            ColumnLayout {
                                Layout.fillWidth:   true
                                Layout.leftMargin:  Theme.AppTheme.marginMd
                                Layout.rightMargin: Theme.AppTheme.marginMd
                                spacing: 2
                                visible: root._queueItem
                                    ? (root._queueItem.metaText || "").length > 0 : false

                                Label {
                                    text:           "Info"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text:           root._queueItem
                                        ? (root._queueItem.metaText || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                        }
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
