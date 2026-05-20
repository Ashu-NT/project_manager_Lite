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

                // ── Approval Queue section title ──────────────────
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
                    }
                }

                // ── Approval Queue toolbar ────────────────────────
                AppWidgets.TableToolbar {
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

                // ── Approval Queue DataTable ──────────────────────
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

                    onRowSelected:  function(id) { root._selectedRowId = id }
                    onRowActivated: function(id) {
                        root._selectedRowId = id
                        const item = root.approvalItemById(id)
                        if (item !== null) decisionDialog.openForDecision("approve", item)
                    }
                }

                // ── Activity feed header ──────────────────────────
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

                // ── Activity timeline feed ────────────────────────
                Item {
                    Layout.fillWidth:       true
                    Layout.preferredHeight: 180

                    ListView {
                        id: _feedList
                        anchors.fill:    parent
                        anchors.topMargin: 4
                        clip:            true
                        boundsBehavior:  Flickable.StopAtBounds
                        spacing:         0
                        model: root.workspaceController
                            ? (root.workspaceController.auditFeed.items || []) : []

                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: Item {
                            id: _feedRow
                            required property var modelData
                            required property int index

                            width:  _feedList.width
                            height: 44

                            // Timeline dot
                            Rectangle {
                                id: _dot
                                anchors.left:           parent.left
                                anchors.leftMargin:     Theme.AppTheme.marginMd
                                anchors.verticalCenter: parent.verticalCenter
                                width: 7; height: 7; radius: 4
                                color: {
                                    const s = (_feedRow.modelData.statusLabel || "").toLowerCase()
                                    if (s.includes("approv") || s.includes("success") || s === "active") return Theme.AppTheme.success
                                    if (s.includes("reject") || s.includes("fail")    || s.includes("error")) return Theme.AppTheme.danger
                                    if (s.includes("warn"))  return Theme.AppTheme.warning
                                    return Theme.AppTheme.textMuted
                                }
                            }

                            // Vertical connector to next item
                            Rectangle {
                                visible:              _feedRow.index < _feedList.count - 1
                                anchors.horizontalCenter: _dot.horizontalCenter
                                anchors.top:          _dot.bottom
                                anchors.topMargin:    2
                                anchors.bottom:       parent.bottom
                                width: 1
                                color: Theme.AppTheme.divider
                            }

                            // Feed item content
                            ColumnLayout {
                                anchors {
                                    left:           _dot.right
                                    leftMargin:     Theme.AppTheme.spacingSm
                                    right:          parent.right
                                    rightMargin:    Theme.AppTheme.marginSm
                                    verticalCenter: parent.verticalCenter
                                }
                                spacing: 2

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing:          Theme.AppTheme.spacingXs

                                    Label {
                                        Layout.fillWidth: true
                                        text:           _feedRow.modelData.title || ""
                                        color:          Theme.AppTheme.textPrimary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        elide:          Text.ElideRight
                                    }

                                    AppWidgets.StatusChip {
                                        visible: (_feedRow.modelData.statusLabel || "").length > 0
                                        status:  _feedRow.modelData.statusLabel || ""
                                    }
                                }

                                Label {
                                    visible:        (_feedRow.modelData.metaText || "").length > 0
                                    text:           _feedRow.modelData.metaText || ""
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide:          Text.ElideRight
                                }
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

            // ── Right detail inspector ────────────────────────────
            Rectangle {
                id: _detailPanel
                Layout.fillHeight:     true
                Layout.preferredWidth: 300
                visible:               root._detailOpen
                color:                 Theme.AppTheme.surfaceRaised
                z:                     1

                // Left border
                Rectangle {
                    anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                    width: 1; color: Theme.AppTheme.divider
                }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // ── Inspector header ──────────────────────────
                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        showBack: true
                        title:    "Request Detail"
                        subtitle: root._queueItem ? (root._queueItem.statusLabel || "") : ""
                        busy:     root._busy
                        actions:  []
                        onBackRequested: root._selectedRowId = ""
                    }

                    // ── Scrollable inspector body ─────────────────
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
                            spacing: 0

                            // Request identity
                            ColumnLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.topMargin:    Theme.AppTheme.marginMd
                                Layout.bottomMargin: Theme.AppTheme.spacingSm
                                spacing:             Theme.AppTheme.spacingSm

                                Label {
                                    Layout.fillWidth: true
                                    text:           root._queueItem ? (root._queueItem.title || "") : ""
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.sectionSize
                                    font.bold:      true
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }

                                AppWidgets.StatusChip {
                                    visible: root._queueItem
                                        ? (root._queueItem.statusLabel || "").length > 0 : false
                                    status: root._queueItem ? (root._queueItem.statusLabel || "") : ""
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // ── Request Details section ───────────
                            AppWidgets.SectionHeading {
                                Layout.fillWidth: true
                                label: "Request Details"
                            }

                            ColumnLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.bottomMargin: Theme.AppTheme.spacingMd
                                spacing:             Theme.AppTheme.spacingSm

                                // Submitted by
                                ColumnLayout {
                                    Layout.fillWidth: true
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
                                        text:    root._queueItem ? (root._queueItem.subtitle || "") : ""
                                        color:   Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                    }
                                }

                                // Module / source
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    visible: root._queueItem
                                        ? (root._queueItem.metaText || "").length > 0 : false

                                    Label {
                                        text:           "Module / Source"
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text:    root._queueItem ? (root._queueItem.metaText || "") : ""
                                        color:   Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                    }
                                }

                                // Context / supporting text
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    visible: root._queueItem
                                        ? (root._queueItem.supportingText || "").length > 0 : false

                                    Label {
                                        text:           "Context"
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text:    root._queueItem ? (root._queueItem.supportingText || "") : ""
                                        color:   Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1; color: Theme.AppTheme.divider
                                visible: root._queueItem !== null
                            }

                            // ── Governance section ────────────────
                            AppWidgets.SectionHeading {
                                Layout.fillWidth: true
                                label: "Governance"
                                visible: root._queueItem !== null
                            }

                            ColumnLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.bottomMargin: Theme.AppTheme.spacingMd
                                spacing:             Theme.AppTheme.spacingSm
                                visible: root._queueItem !== null

                                // Required action
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text:           "Required action"
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: {
                                            if (!root._queueItem) return ""
                                            const s = (root._queueItem.statusLabel || "").toLowerCase()
                                            return s.includes("pending") ? "Awaiting your decision"
                                                                         : "Decision already recorded"
                                        }
                                        color:   Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                    }
                                }

                                // Request ID
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text:           "Request ID"
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text:  root._queueItem ? String(root._queueItem.id || "") : ""
                                        color: Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    // ── Bottom action footer ──────────────────────
                    Rectangle {
                        Layout.fillWidth: true
                        height: Theme.AppTheme.toolbarHeight
                        color:  Theme.AppTheme.surfaceRaised

                        Rectangle {
                            anchors { top: parent.top; left: parent.left; right: parent.right }
                            height: 1; color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            anchors.fill:        parent
                            anchors.leftMargin:  Theme.AppTheme.marginMd
                            anchors.rightMargin: Theme.AppTheme.marginMd
                            spacing:             Theme.AppTheme.spacingSm

                            AppControls.PrimaryButton {
                                Layout.fillWidth: true
                                text:     "Approve"
                                iconName: "approve"
                                enabled:  !root._busy && root._queueItem !== null
                                onClicked: {
                                    const item = root._queueItem
                                    if (item !== null) decisionDialog.openForDecision("approve", item)
                                }
                            }

                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text:     "Reject"
                                iconName: "reject"
                                danger:   true
                                enabled:  !root._busy && root._queueItem !== null
                                onClicked: {
                                    const item = root._queueItem
                                    if (item !== null) decisionDialog.openForDecision("reject", item)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Filter popup ──────────────────────────────────────────────
    Popup {
        id: approvalFilterPopup
        parent:      Overlay.overlay
        anchors.centerIn: parent
        width:       320
        padding:     Theme.AppTheme.marginMd
        modal:       true
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

            Label {
                text:           "Filter Approvals"
                color:          Theme.AppTheme.textPrimary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold:      true
            }

            Label {
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
    Popup {
        id: approvalViewsPopup
        parent:      Overlay.overlay
        anchors.centerIn: parent
        width:       220
        padding:     4
        modal:       true
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

                    Label {
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
