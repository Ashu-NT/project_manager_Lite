pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root

    // ── External dependencies ─────────────────────────────────────────────
    property var workspaceController: null
    property var shellModel: null

    // ── Models (bound to controller) ──────────────────────────────────────
    readonly property var inboxPanelModel: root.workspaceController
        ? root.workspaceController.inbox
        : ({ "title": "Inbox", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var mentionsPanelModel: root.workspaceController
        ? root.workspaceController.mentions
        : ({ "title": "Mentions", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var approvalsPanelModel: root.workspaceController
        ? root.workspaceController.approvals
        : ({ "title": "Approvals", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var activityPanelModel: root.workspaceController
        ? root.workspaceController.activityFeed
        : ({ "title": "Activity", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var selectedDetailModel: root.workspaceController
        ? root.workspaceController.selectedItemDetail
        : ({
            "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "",
            "state": {}, "fields": [],
            "activity": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
            "relatedItems": { "title": "", "subtitle": "", "emptyState": "", "items": [] }
        })

    // ── Filter state (readonly from controller) ───────────────────────────
    readonly property string selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : "all"
    readonly property string selectedTeamId: root.workspaceController ? root.workspaceController.selectedTeamId : "all"
    readonly property string selectedPeriodKey: root.workspaceController ? root.workspaceController.selectedPeriodKey : "all"
    readonly property string selectedUnreadKey: root.workspaceController ? root.workspaceController.selectedUnreadKey : "all"
    readonly property string inboxSearchText: root.workspaceController ? root.workspaceController.inboxSearchText : ""
    readonly property string mentionsSearchText: root.workspaceController ? root.workspaceController.mentionsSearchText : ""

    // ── Pagination state ──────────────────────────────────────────────────

    // ── Selection state ───────────────────────────────────────────────────
    property string activePanelId: "inbox"
    property string _selectedRowId: ""
    readonly property bool _detailOpen: String(root.selectedDetailModel.id || "").length > 0

    // ── Column definitions ────────────────────────────────────────────────
    readonly property var _inboxColumns: [
        { "key": "title",          "label": "Workflow Item", "preferredWidth": 260, "sortable": true },
        { "key": "workflowType",   "label": "Type",          "preferredWidth": 140 },
        { "key": "projectName",    "label": "Project",       "preferredWidth": 180 },
        { "key": "supportingText", "label": "Summary",       "preferredWidth": 240 },
        { "key": "statusLabel",    "label": "Status",        "preferredWidth": 140, "type": "status" }
    ]
    readonly property var _mentionsColumns: [
        { "key": "title",      "label": "Mention",  "preferredWidth": 260, "sortable": true },
        { "key": "sourceName", "label": "Source",   "preferredWidth": 220 },
        { "key": "actorLabel", "label": "User",     "preferredWidth": 140 },
        { "key": "metaText",   "label": "Date",     "preferredWidth": 140 },
        { "key": "statusLabel","label": "Status",   "preferredWidth": 120, "type": "status" }
    ]
    readonly property var _approvalsColumns: [
        { "key": "title",        "label": "Approval Item", "preferredWidth": 260, "sortable": true },
        { "key": "approvalType", "label": "Type",          "preferredWidth": 140 },
        { "key": "requestor",    "label": "Requestor",     "preferredWidth": 150 },
        { "key": "moduleLabel",  "label": "Module",        "preferredWidth": 160 },
        { "key": "statusLabel",  "label": "Status",        "preferredWidth": 120, "type": "status" }
    ]

    // ── Computed current panel state ──────────────────────────────────────
    readonly property var _currentPanelModel: {
        if (root.activePanelId === "mentions") return root.mentionsPanelModel
        if (root.activePanelId === "approvals") return root.approvalsPanelModel
        if (root.activePanelId === "activity") return root.activityPanelModel
        return root.inboxPanelModel
    }
    readonly property var _currentTableColumns: {
        if (root.activePanelId === "mentions") return root._mentionsColumns
        if (root.activePanelId === "approvals") return root._approvalsColumns
        return root._inboxColumns
    }
    readonly property int _currentTablePage: root._panelPage(root.activePanelId)
    readonly property int _currentTablePageSize: root._panelPageSize(root.activePanelId)
    readonly property var _currentTableRows: {
        if (root.activePanelId === "mentions") return root._mentionRows
        if (root.activePanelId === "approvals") return root._approvalRows
        return root._inboxRows
    }
    readonly property int _currentTableTotalItems: root.activePanelId === "mentions"
        ? Number(root.mentionsPanelModel.totalCount || 0)
        : (root.activePanelId === "inbox"
            ? Number(root.inboxPanelModel.totalCount || 0)
            : root._currentTableRows.length)
    readonly property int _currentTablePageCount: Math.max(
        1, Math.ceil(root._currentTableTotalItems / Math.max(1, root._currentTablePageSize))
    )
    readonly property int _effectiveTablePage: Math.min(root._currentTablePage, root._currentTablePageCount)
    readonly property var _selectedRowItem: root._rowById(root._selectedRowId, root._currentTableRows)

    readonly property var _currentContextActions: {
        const item = root._selectedRowItem
        const panel = root.activePanelId
        if (!item) {
            if (panel === "approvals") return [
                { "id": "approve",     "label": "Approve",  "icon": "approve",   "enabled": false },
                { "id": "reject",      "label": "Reject",   "icon": "close",     "enabled": false, "danger": true },
                { "id": "open_source", "label": "Open Item","icon": "view",      "enabled": false }
            ]
            if (panel === "mentions" || panel === "inbox") return [
                { "id": "mark_read",   "label": "Mark Read",                        "icon": "approve",  "enabled": false },
                { "id": "open_source", "label": panel === "mentions" ? "Open Source" : "Open Task", "icon": "view", "enabled": false }
            ]
            return [{ "id": "open_source", "label": "Open Source", "icon": "view", "enabled": false }]
        }
        if (panel === "approvals") {
            const isPending = String(item.statusLabel || "").toLowerCase().indexOf("pending") >= 0
            return [
                { "id": "approve",     "label": "Approve",  "icon": "approve",  "enabled": isPending },
                { "id": "reject",      "label": "Reject",   "icon": "close",    "enabled": isPending, "danger": true },
                { "id": "open_source", "label": "Open Item","icon": "view",     "enabled": true }
            ]
        }
        if (panel === "mentions" || panel === "inbox") return [
            { "id": "mark_read",   "label": "Mark Read",  "icon": "approve",  "enabled": !!(item.state && item.state.taskId) },
            { "id": "open_source", "label": panel === "mentions" ? "Open Source" : "Open Task", "icon": "view", "enabled": true }
        ]
        return [{ "id": "open_source", "label": "Open Source", "icon": "view", "enabled": true }]
    }

    // ── Filtered/built rows ───────────────────────────────────────────────
    readonly property var _inboxRows: root._buildInboxRows(root.inboxPanelModel.items || [])
    readonly property var _mentionRows: root._buildMentionRows(root.mentionsPanelModel.items || [])
    readonly property var _approvalRows: root._buildApprovalRows(root.approvalsPanelModel.items || [])
    readonly property var _activityFeedItems: root.activityPanelModel.items || []

    // ── Event handlers ────────────────────────────────────────────────────
    onActivePanelIdChanged: {
        root._selectedRowId = ""
        root._resetPanelPage(root.activePanelId)
        if (root.workspaceController !== null) root.workspaceController.clearSelection()
    }
    onSelectedProjectIdChanged: root._resetAllTablePages()
    onSelectedTeamIdChanged: root._resetAllTablePages()
    onSelectedPeriodKeyChanged: root._resetAllTablePages()
    onSelectedUnreadKeyChanged: root._resetAllTablePages()

    // ── Lookup helpers ────────────────────────────────────────────────────
    function _rowById(rowId, rows) {
        const list = rows || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === String(rowId || "")) return list[i]
        }
        return null
    }

    // ── Search/filter state accessors ─────────────────────────────────────
    function _panelSearchText(panelId) {
        if (panelId === "mentions") return root.mentionsSearchText
        return root.inboxSearchText
    }

    function _setPanelSearchText(panelId, text) {
        if (!root.workspaceController) return
        if (panelId === "mentions")      root.workspaceController.setMentionsSearchText(text)
        else if (panelId === "inbox") root.workspaceController.setInboxSearchText(text)
        root._resetPanelPage(panelId)
    }

    // ── Pagination helpers ────────────────────────────────────────────────
    function _panelPage(panelId) {
        if (panelId === "mentions") return Number(root.mentionsPanelModel.page || 1)
        if (panelId === "inbox") return Number(root.inboxPanelModel.page || 1)
        return 1
    }

    function _setPanelPage(panelId, page) {
        const nextPage = Math.max(1, Number(page) || 1)
        if (panelId === "mentions") {
            if (root.workspaceController) root.workspaceController.setMentionsPage(nextPage)
        }
        else if (panelId === "inbox" && root.workspaceController)
            root.workspaceController.setInboxPage(nextPage)
    }

    function _panelPageSize(panelId) {
        if (panelId === "mentions") return Number(root.mentionsPanelModel.pageSize || 25)
        if (panelId === "inbox") return Number(root.inboxPanelModel.pageSize || 25)
        return 25
    }

    function _setPanelPageSize(panelId, pageSize) {
        const nextPageSize = Math.max(1, Number(pageSize) || 25)
        if (panelId === "mentions") {
            if (root.workspaceController) root.workspaceController.setMentionsPageSize(nextPageSize)
        }
        else if (panelId === "inbox" && root.workspaceController)
            root.workspaceController.setInboxPageSize(nextPageSize)
        root._resetPanelPage(panelId)
    }

    function _resetPanelPage(panelId) { root._setPanelPage(panelId, 1) }

    function _resetAllTablePages() {
        if (!root.workspaceController) return
        root.workspaceController.setInboxPage(1)
        root.workspaceController.setMentionsPage(1)
    }

    // ── Text formatting ───────────────────────────────────────────────────
    function _formatTitleCase(value) {
        const raw = String(value || "").replace(/_/g, " ").trim()
        if (raw.length === 0) return ""
        const words = raw.split(" ")
        for (let i = 0; i < words.length; i++) {
            const word = String(words[i] || "")
            if (word.length > 0) words[i] = word.charAt(0).toUpperCase() + word.slice(1)
        }
        return words.join(" ")
    }

    // ── Global filter matching ────────────────────────────────────────────
    // ── Row builders ──────────────────────────────────────────────────────
    function _buildInboxRows(items) {
        const rows = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            const st = item.state || {}
            rows.push({ "id": item.id, "title": item.title, "workflowType": "Mention",
                "projectName": st.projectName || "", "supportingText": item.supportingText || "",
                "statusLabel": item.statusLabel || "", "subtitle": item.subtitle || "", "metaText": item.metaText || "", "state": st })
        }
        return rows
    }

    function _buildMentionRows(items) {
        const rows = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            const st = item.state || {}
            rows.push({ "id": item.id, "title": item.title, "sourceName": st.taskId || item.subtitle || "",
                "actorLabel": st.actorUsername ? ("@" + st.actorUsername) : "", "metaText": item.metaText || "",
                "statusLabel": item.statusLabel || "", "subtitle": item.subtitle || "", "supportingText": item.supportingText || "", "state": st })
        }
        return rows
    }

    function _buildApprovalRows(items) {
        const rows = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            const st = item.state || {}
            rows.push({ "id": item.id, "title": item.title, "approvalType": root._formatTitleCase(st.requestType || st.entityType || "approval"),
                "requestor": st.requestor ? ("@" + st.requestor) : "", "moduleLabel": st.moduleLabel || "",
                "statusLabel": item.statusLabel || "", "subtitle": item.subtitle || "", "supportingText": item.supportingText || "", "metaText": item.metaText || "", "state": st })
        }
        return rows
    }

    function _openRow(panelId, rowId) {
        root._selectedRowId = String(rowId || "")
        if (root.workspaceController !== null && root._selectedRowId.length > 0)
            root.workspaceController.selectItem(panelId, root._selectedRowId)
    }

    function _navigateRoute(routeId) {
        if (root.shellModel && String(routeId || "").length > 0)
            root.shellModel.selectRoute(String(routeId || ""))
    }

    function _handleCurrentAction(actionId) {
        const item = root._selectedRowItem
        if (!item || root.workspaceController === null) return
        const st = item.state || {}
        if (actionId === "mark_read") root.workspaceController.markItemRead(root.activePanelId, item.id)
        else if (actionId === "approve") root.workspaceController.approveRequest(String(st.requestId || ""))
        else if (actionId === "reject") root.workspaceController.rejectRequest(String(st.requestId || ""))
        else if (actionId === "open_source") root._navigateRoute(String(st.routeId || ""))
    }

    function _handleDetailAction(actionId) {
        const st = root.selectedDetailModel.state || {}
        if (actionId === "back") {
            root.workspaceController.clearSelection()
            root._selectedRowId = ""
            return
        }
        if (actionId === "mark_read") {
            root.workspaceController.markItemRead(String(st.panelId || root.activePanelId), String(root.selectedDetailModel.id || ""))
            return
        }
        if (actionId === "approve") { root.workspaceController.approveRequest(String(st.requestId || "")); return }
        if (actionId === "reject") { root.workspaceController.rejectRequest(String(st.requestId || "")); return }
        if (actionId === "open_source") root._navigateRoute(String(st.routeId || ""))
    }

    function _detailActions() {
        const st = root.selectedDetailModel.state || {}
        const panelId = String(st.panelId || root.activePanelId)
        if (panelId === "approvals") {
            const pending = String(st.status || "").toLowerCase() === "pending"
            return [
                { "id": "approve",     "label": "Approve",      "icon": "approve", "enabled": pending },
                { "id": "reject",      "label": "Reject",       "icon": "close",   "enabled": pending, "danger": true },
                { "id": "open_source", "label": "Open Source",  "icon": "view",    "enabled": true }
            ]
        }
        return [
            { "id": "mark_read",   "label": "Mark Read",   "icon": "approve", "enabled": !!(st.taskId) },
            { "id": "open_source", "label": "Open Source", "icon": "view",    "enabled": true }
        ]
    }
}
