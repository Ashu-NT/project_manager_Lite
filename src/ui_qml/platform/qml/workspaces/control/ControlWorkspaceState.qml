pragma ComponentBehavior: Bound
import QtQuick
import Platform.Controllers 1.0 as PlatformControllers

Item {
    id: root

    // ── Injected ──────────────────────────────────────────────────────────
    property PlatformControllers.PlatformControlWorkspaceController workspaceController

    // ── UI state ──────────────────────────────────────────────────────────
    property string selectedRowId:      ""
    property string searchText:         ""
    property string activePanel:        "approvals"
    property int    queuePageSize:      50
    property int    queueCurrentPage:   0
    property bool   approvalDetailOpen: false

    // ── Computed ──────────────────────────────────────────────────────────
    readonly property bool detailOpen: root.approvalDetailOpen && root.activePanel === "approvals"

    readonly property int queueTotalCount: root.workspaceController
        ? (root.workspaceController.approvalQueue.items || []).length : 0
    readonly property int queuePageCount: Math.max(1, Math.ceil(root.queueTotalCount / root.queuePageSize))

    readonly property int queueCount: root.workspaceController
        ? (root.workspaceController.approvalQueue.items || []).length : 0
    readonly property int feedCount: root.workspaceController
        ? (root.workspaceController.auditFeed.items || []).length : 0

    readonly property var queueItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.workspaceController
            ? (root.workspaceController.approvalQueue.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    // ── Column definitions ────────────────────────────────────────────────
    readonly property var queueColumns: [
        { key: "title",       label: "Request",       flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Submitted by",  flex: 2, minWidth: 120, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",        flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Module / Info", flex: 2, minWidth: 120, sortable: false, visible: true }
    ]

    // ── Helpers ───────────────────────────────────────────────────────────
    function approvalItemById(itemId) {
        const items = root.workspaceController
            ? (root.workspaceController.approvalQueue.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }
}
