pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root

    // ── External dependencies ─────────────────────────────────────────────
    property var workspaceController: null
    property var shellModel: null

    // ── Models (bound to controller) ──────────────────────────────────────
    readonly property var inboxPanelModel: root.workspaceController
        ? root.workspaceController.notifications
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
    readonly property var teamUpdatesPanelModel: root.workspaceController
        ? root.workspaceController.teamUpdates
        : ({ "title": "Team Updates", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var selectedDetailModel: root.workspaceController
        ? root.workspaceController.selectedItemDetail
        : ({
            "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "",
            "state": {}, "fields": [],
            "activity": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
            "relatedItems": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
            "audit": { "title": "", "subtitle": "", "emptyState": "", "items": [] }
        })

    // ── Filter state (readonly from controller) ───────────────────────────
    readonly property string selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : "all"
    readonly property string selectedTeamId: root.workspaceController ? root.workspaceController.selectedTeamId : "all"
    readonly property string selectedPeriodKey: root.workspaceController ? root.workspaceController.selectedPeriodKey : "all"
    readonly property string selectedUnreadKey: root.workspaceController ? root.workspaceController.selectedUnreadKey : "all"
    readonly property string inboxSearchText: root.workspaceController ? root.workspaceController.inboxSearchText : ""
    readonly property string mentionsSearchText: root.workspaceController ? root.workspaceController.mentionsSearchText : ""
    readonly property string approvalsSearchText: root.workspaceController ? root.workspaceController.approvalsSearchText : ""
    property string activitySearchText: ""
    readonly property string teamUpdatesSearchText: root.workspaceController ? root.workspaceController.teamUpdatesSearchText : ""

    // ── Pagination state ──────────────────────────────────────────────────
    property int inboxPage: 1
    property int mentionsPage: 1
    property int approvalsPage: 1
    property int teamUpdatesPage: 1
    property int inboxPageSize: 25
    property int mentionsPageSize: 25
    property int approvalsPageSize: 25
    property int teamUpdatesPageSize: 25

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
    readonly property var _teamUpdatesColumns: [
        { "key": "title",        "label": "User",      "preferredWidth": 220, "sortable": true },
        { "key": "activityType", "label": "Activity",  "preferredWidth": 140, "type": "status" },
        { "key": "sourceName",   "label": "Task",      "preferredWidth": 240 },
        { "key": "projectName",  "label": "Project",   "preferredWidth": 180 },
        { "key": "metaText",     "label": "Last Seen", "preferredWidth": 160 }
    ]

    // ── Computed current panel state ──────────────────────────────────────
    readonly property var _currentPanelModel: {
        if (root.activePanelId === "mentions") return root.mentionsPanelModel
        if (root.activePanelId === "approvals") return root.approvalsPanelModel
        if (root.activePanelId === "activity") return root.activityPanelModel
        if (root.activePanelId === "team_updates") return root.teamUpdatesPanelModel
        return root.inboxPanelModel
    }
    readonly property var _currentTableColumns: {
        if (root.activePanelId === "mentions") return root._mentionsColumns
        if (root.activePanelId === "approvals") return root._approvalsColumns
        if (root.activePanelId === "team_updates") return root._teamUpdatesColumns
        return root._inboxColumns
    }
    readonly property int _currentTablePage: root._panelPage(root.activePanelId)
    readonly property int _currentTablePageSize: root._panelPageSize(root.activePanelId)
    readonly property var _currentTableRows: {
        if (root.activePanelId === "mentions") return root._mentionRows
        if (root.activePanelId === "approvals") return root._approvalRows
        if (root.activePanelId === "team_updates") return root._teamUpdateRows
        return root._inboxRows
    }
    readonly property int _currentTableTotalItems: root._currentTableRows.length
    readonly property int _currentTablePageCount: Math.max(
        1, Math.ceil(root._currentTableTotalItems / Math.max(1, root._currentTablePageSize))
    )
    readonly property int _effectiveTablePage: Math.min(root._currentTablePage, root._currentTablePageCount)
    readonly property var _currentPagedRows: {
        const start = (root._effectiveTablePage - 1) * root._currentTablePageSize
        return root._currentTableRows.slice(start, start + root._currentTablePageSize)
    }
    readonly property var _selectedRowItem: root._rowById(root._selectedRowId, root._currentTableRows)

    readonly property var _currentContextActions: {
        const item = root._selectedRowItem
        const panel = root.activePanelId
        if (!item) {
            if (panel === "approvals") return [
                { "id": "approve",     "label": "Approve",  "icon": "approve",   "enabled": false },
                { "id": "reject",      "label": "Reject",   "icon": "close",     "enabled": false, "danger": true },
                { "id": "delegate",    "label": "Delegate", "icon": "workflow",  "enabled": false },
                { "id": "open_source", "label": "Open Item","icon": "open",      "enabled": false }
            ]
            if (panel === "mentions" || panel === "inbox") return [
                { "id": "mark_read",   "label": "Mark Read",                        "icon": "approve",  "enabled": false },
                { "id": "assign",      "label": "Assign",                           "icon": "workflow", "enabled": false },
                { "id": "archive",     "label": "Archive",                          "icon": "close",    "enabled": false },
                { "id": "open_source", "label": panel === "mentions" ? "Open Source" : "Open Task", "icon": "open", "enabled": false }
            ]
            return [{ "id": "open_source", "label": "Open Source", "icon": "open", "enabled": false }]
        }
        if (panel === "approvals") {
            const isPending = String(item.statusLabel || "").toLowerCase().indexOf("pending") >= 0
            return [
                { "id": "approve",     "label": "Approve",  "icon": "approve",  "enabled": isPending },
                { "id": "reject",      "label": "Reject",   "icon": "close",    "enabled": isPending, "danger": true },
                { "id": "delegate",    "label": "Delegate", "icon": "workflow", "enabled": false },
                { "id": "open_source", "label": "Open Item","icon": "open",     "enabled": true }
            ]
        }
        if (panel === "mentions" || panel === "inbox") return [
            { "id": "mark_read",   "label": "Mark Read",  "icon": "approve",  "enabled": !!(item.state && item.state.taskId) },
            { "id": "assign",      "label": "Assign",     "icon": "workflow", "enabled": false },
            { "id": "archive",     "label": "Archive",    "icon": "close",    "enabled": false },
            { "id": "open_source", "label": panel === "mentions" ? "Open Source" : "Open Task", "icon": "open", "enabled": true }
        ]
        return [{ "id": "open_source", "label": "Open Source", "icon": "open", "enabled": true }]
    }

    // ── Filtered/built rows ───────────────────────────────────────────────
    readonly property var _inboxRows: root._buildInboxRows(root.inboxPanelModel.items || [])
    readonly property var _mentionRows: root._buildMentionRows(root.mentionsPanelModel.items || [])
    readonly property var _approvalRows: root._buildApprovalRows(root.approvalsPanelModel.items || [])
    readonly property var _activityFeedItems: root._filterFeedItems(root.activityPanelModel.items || [], root.activitySearchText)
    readonly property var _teamUpdateRows: root._buildTeamUpdateRows(root.teamUpdatesPanelModel.items || [])

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
        if (panelId === "approvals") return root.approvalsSearchText
        if (panelId === "activity") return root.activitySearchText
        if (panelId === "team_updates") return root.teamUpdatesSearchText
        return root.inboxSearchText
    }

    function _setPanelSearchText(panelId, text) {
        if (!root.workspaceController) return
        if (panelId === "mentions")      root.workspaceController.setMentionsSearchText(text)
        else if (panelId === "approvals") root.workspaceController.setApprovalsSearchText(text)
        else if (panelId === "activity")  root.activitySearchText = text
        else if (panelId === "team_updates") root.workspaceController.setTeamUpdatesSearchText(text)
        else root.workspaceController.setInboxSearchText(text)
        root._resetPanelPage(panelId)
    }

    // ── Pagination helpers ────────────────────────────────────────────────
    function _panelPage(panelId) {
        if (panelId === "mentions") return root.mentionsPage
        if (panelId === "approvals") return root.approvalsPage
        if (panelId === "team_updates") return root.teamUpdatesPage
        return root.inboxPage
    }

    function _setPanelPage(panelId, page) {
        const nextPage = Math.max(1, Number(page) || 1)
        if (panelId === "mentions") root.mentionsPage = nextPage
        else if (panelId === "approvals") root.approvalsPage = nextPage
        else if (panelId === "team_updates") root.teamUpdatesPage = nextPage
        else root.inboxPage = nextPage
    }

    function _panelPageSize(panelId) {
        if (panelId === "mentions") return root.mentionsPageSize
        if (panelId === "approvals") return root.approvalsPageSize
        if (panelId === "team_updates") return root.teamUpdatesPageSize
        return root.inboxPageSize
    }

    function _setPanelPageSize(panelId, pageSize) {
        const nextPageSize = Math.max(1, Number(pageSize) || 25)
        if (panelId === "mentions") root.mentionsPageSize = nextPageSize
        else if (panelId === "approvals") root.approvalsPageSize = nextPageSize
        else if (panelId === "team_updates") root.teamUpdatesPageSize = nextPageSize
        else root.inboxPageSize = nextPageSize
        root._resetPanelPage(panelId)
    }

    function _resetPanelPage(panelId) { root._setPanelPage(panelId, 1) }

    function _resetAllTablePages() {
        root.inboxPage = 1; root.mentionsPage = 1; root.approvalsPage = 1; root.teamUpdatesPage = 1
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
    function _matchesGlobalFilters(item) {
        const st = item && item.state ? item.state : {}
        if (root.selectedProjectId !== "all" && String(st.projectId || "") !== String(root.selectedProjectId || "")) return false
        const teamKey = String(st.actorUsername || st.requestor || st.username || "")
        if (root.selectedTeamId !== "all" && teamKey !== String(root.selectedTeamId || "")) return false
        if (root.selectedUnreadKey === "unread" && !Boolean(st.unread)) return false
        if (root.selectedUnreadKey === "attention" && !Boolean(st.attention)) return false
        if (root.selectedPeriodKey !== "all") {
            if (!root._matchesPeriod(String(st.createdAt || ""))) return false
        }
        return true
    }

    function _matchesPeriod(createdAtIso) {
        if (!createdAtIso || root.selectedPeriodKey === "all") return true
        const observed = new Date(createdAtIso)
        if (isNaN(observed.getTime())) return true
        const now = new Date()
        const deltaMs = now.getTime() - observed.getTime()
        if (root.selectedPeriodKey === "24h") return deltaMs <= 24 * 60 * 60 * 1000
        if (root.selectedPeriodKey === "7d") return deltaMs <= 7 * 24 * 60 * 60 * 1000
        if (root.selectedPeriodKey === "30d") return deltaMs <= 30 * 24 * 60 * 60 * 1000
        return true
    }

    function _matchesSearch(item, searchText) {
        const query = String(searchText || "").trim().toLowerCase()
        if (query.length === 0) return true
        const haystack = [item.title, item.subtitle, item.supportingText, item.metaText, item.statusLabel].join(" ").toLowerCase()
        return haystack.indexOf(query) >= 0
    }

    // ── Row builders ──────────────────────────────────────────────────────
    function _buildInboxRows(items) {
        const rows = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.inboxSearchText)) continue
            const st = item.state || {}
            rows.push({ "id": item.id, "title": item.title, "workflowType": root._formatTitleCase(st.notificationType || "workflow"),
                "projectName": st.projectName || "Cross-project", "supportingText": item.supportingText || "",
                "statusLabel": item.statusLabel || "", "subtitle": item.subtitle || "", "metaText": item.metaText || "", "state": st })
        }
        return rows
    }

    function _buildMentionRows(items) {
        const rows = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.mentionsSearchText)) continue
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
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.approvalsSearchText)) continue
            const st = item.state || {}
            rows.push({ "id": item.id, "title": item.title, "approvalType": root._formatTitleCase(st.requestType || st.entityType || "approval"),
                "requestor": st.requestor ? ("@" + st.requestor) : "", "moduleLabel": st.moduleLabel || "",
                "statusLabel": item.statusLabel || "", "subtitle": item.subtitle || "", "supportingText": item.supportingText || "", "metaText": item.metaText || "", "state": st })
        }
        return rows
    }

    function _buildTeamUpdateRows(items) {
        const rows = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.teamUpdatesSearchText)) continue
            const st = item.state || {}
            rows.push({ "id": item.id, "title": item.title, "activityType": item.statusLabel || "",
                "sourceName": st.taskName || item.subtitle || "", "projectName": st.projectName || "",
                "metaText": item.supportingText || "", "subtitle": item.subtitle || "", "supportingText": item.supportingText || "", "statusLabel": item.statusLabel || "", "state": st })
        }
        return rows
    }

    function _filterFeedItems(items, searchText) {
        const list = []
        for (let i = 0; i < (items || []).length; i++) {
            const item = items[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, searchText)) continue
            list.push(item)
        }
        return list
    }

    function _clearFilters() {
        if (root.workspaceController !== null) {
            root.workspaceController.setSelectedProjectId("all")
            root.workspaceController.setSelectedTeamId("all")
            root.workspaceController.setSelectedPeriodKey("all")
            root.workspaceController.setSelectedUnreadKey("all")
        }
        root._resetAllTablePages()
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
                { "id": "open_source", "label": "Open Source",  "icon": "open",    "enabled": true }
            ]
        }
        return [
            { "id": "mark_read",   "label": "Mark Read",   "icon": "approve", "enabled": !!(st.taskId) },
            { "id": "open_source", "label": "Open Source", "icon": "open",    "enabled": true }
        ]
    }
}
