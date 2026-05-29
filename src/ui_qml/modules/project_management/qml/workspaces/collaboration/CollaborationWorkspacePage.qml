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

AppLayouts.WorkspaceFrame {
    id: root

    property ShellContexts.ShellContext shellModel
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementCollaborationWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.collaborationWorkspace
        : null

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.collaboration",
            "title": "Collaboration",
            "summary": "Workflow inbox, operational communication, mentions, approvals, and activity feed."
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var contextModel: root.workspaceController
        ? root.workspaceController.context
        : ({
            "projectOptions": [],
            "teamOptions": [],
            "periodOptions": [],
            "unreadOptions": []
        })
    readonly property var panelTabsModel: root.workspaceController
        ? (root.workspaceController.panelTabs || [])
        : []
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
    readonly property var auditPanelModel: root.workspaceController
        ? root.workspaceController.auditFeed
        : ({ "title": "Audit", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var selectedDetailModel: root.workspaceController
        ? root.workspaceController.selectedItemDetail
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "state": {},
            "fields": [],
            "activity": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
            "relatedItems": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
            "audit": { "title": "", "subtitle": "", "emptyState": "", "items": [] }
        })

    property string activePanelId: "inbox"
    property string selectedProjectId: "all"
    property string selectedTeamId: "all"
    property string selectedPeriodKey: "all"
    property string selectedUnreadKey: "all"
    property string inboxSearchText: ""
    property string mentionsSearchText: ""
    property string approvalsSearchText: ""
    property string activitySearchText: ""
    property string teamUpdatesSearchText: ""
    property string auditSearchText: ""
    property int inboxPage: 1
    property int mentionsPage: 1
    property int approvalsPage: 1
    property int teamUpdatesPage: 1
    property int inboxPageSize: 25
    property int mentionsPageSize: 25
    property int approvalsPageSize: 25
    property int teamUpdatesPageSize: 25
    property string _selectedRowId: ""
    readonly property bool _detailOpen: String(root.selectedDetailModel.id || "").length > 0

    readonly property var _inboxColumns: [
        { "key": "title", "label": "Workflow Item", "preferredWidth": 260, "sortable": true },
        { "key": "workflowType", "label": "Type", "preferredWidth": 140 },
        { "key": "projectName", "label": "Project", "preferredWidth": 180 },
        { "key": "supportingText", "label": "Summary", "preferredWidth": 240 },
        { "key": "statusLabel", "label": "Status", "preferredWidth": 140, "type": "status" }
    ]
    readonly property var _mentionsColumns: [
        { "key": "title", "label": "Mention", "preferredWidth": 260, "sortable": true },
        { "key": "sourceName", "label": "Source", "preferredWidth": 220 },
        { "key": "actorLabel", "label": "User", "preferredWidth": 140 },
        { "key": "metaText", "label": "Date", "preferredWidth": 140 },
        { "key": "statusLabel", "label": "Status", "preferredWidth": 120, "type": "status" }
    ]
    readonly property var _approvalsColumns: [
        { "key": "title", "label": "Approval Item", "preferredWidth": 260, "sortable": true },
        { "key": "approvalType", "label": "Type", "preferredWidth": 140 },
        { "key": "requestor", "label": "Requestor", "preferredWidth": 150 },
        { "key": "moduleLabel", "label": "Module", "preferredWidth": 160 },
        { "key": "statusLabel", "label": "Status", "preferredWidth": 120, "type": "status" }
    ]
    readonly property var _teamUpdatesColumns: [
        { "key": "title", "label": "User", "preferredWidth": 220, "sortable": true },
        { "key": "activityType", "label": "Activity", "preferredWidth": 140, "type": "status" },
        { "key": "sourceName", "label": "Task", "preferredWidth": 240 },
        { "key": "projectName", "label": "Project", "preferredWidth": 180 },
        { "key": "metaText", "label": "Last Seen", "preferredWidth": 160 }
    ]

    readonly property var _currentPanelModel: {
        if (root.activePanelId === "mentions") return root.mentionsPanelModel
        if (root.activePanelId === "approvals") return root.approvalsPanelModel
        if (root.activePanelId === "activity") return root.activityPanelModel
        if (root.activePanelId === "team_updates") return root.teamUpdatesPanelModel
        if (root.activePanelId === "audit") return root.auditPanelModel
        return root.inboxPanelModel
    }
    readonly property var _currentTableRows: {
        if (root.activePanelId === "mentions") return root._mentionRows
        if (root.activePanelId === "approvals") return root._approvalRows
        if (root.activePanelId === "team_updates") return root._teamUpdateRows
        return root._inboxRows
    }
    readonly property var _currentTableColumns: {
        if (root.activePanelId === "mentions") return root._mentionsColumns
        if (root.activePanelId === "approvals") return root._approvalsColumns
        if (root.activePanelId === "team_updates") return root._teamUpdatesColumns
        return root._inboxColumns
    }
    readonly property int _currentTablePage: root._panelPage(root.activePanelId)
    readonly property int _currentTablePageSize: root._panelPageSize(root.activePanelId)
    readonly property int _currentTableTotalItems: root._currentTableRows.length
    readonly property int _currentTablePageCount: Math.max(
        1,
        Math.ceil(root._currentTableTotalItems / Math.max(1, root._currentTablePageSize))
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
            if (panel === "approvals") {
                return [
                    { "id": "approve", "label": "Approve", "icon": "approve", "enabled": false, "danger": false },
                    { "id": "reject", "label": "Reject", "icon": "close", "enabled": false, "danger": true },
                    { "id": "delegate", "label": "Delegate", "icon": "workflow", "enabled": false, "danger": false },
                    { "id": "open_source", "label": "Open Item", "icon": "open", "enabled": false, "danger": false }
                ]
            }
            if (panel === "mentions" || panel === "inbox") {
                return [
                    { "id": "mark_read", "label": "Mark Read", "icon": "approve", "enabled": false, "danger": false },
                    { "id": "assign", "label": "Assign", "icon": "workflow", "enabled": false, "danger": false },
                    { "id": "archive", "label": "Archive", "icon": "close", "enabled": false, "danger": false },
                    { "id": "open_source", "label": panel === "mentions" ? "Open Source" : "Open Task", "icon": "open", "enabled": false, "danger": false }
                ]
            }
            return [
                { "id": "open_source", "label": "Open Source", "icon": "open", "enabled": false, "danger": false }
            ]
        }
        if (panel === "approvals") {
            const isPending = String(item.statusLabel || "").toLowerCase().indexOf("pending") >= 0
            return [
                { "id": "approve", "label": "Approve", "icon": "approve", "enabled": isPending, "danger": false },
                { "id": "reject", "label": "Reject", "icon": "close", "enabled": isPending, "danger": true },
                { "id": "delegate", "label": "Delegate", "icon": "workflow", "enabled": false, "danger": false },
                { "id": "open_source", "label": "Open Item", "icon": "open", "enabled": true, "danger": false }
            ]
        }
        if (panel === "mentions" || panel === "inbox") {
            return [
                { "id": "mark_read", "label": "Mark Read", "icon": "approve", "enabled": !!(item.state && item.state.taskId), "danger": false },
                { "id": "assign", "label": "Assign", "icon": "workflow", "enabled": false, "danger": false },
                { "id": "archive", "label": "Archive", "icon": "close", "enabled": false, "danger": false },
                { "id": "open_source", "label": panel === "mentions" ? "Open Source" : "Open Task", "icon": "open", "enabled": true, "danger": false }
            ]
        }
        return [
            { "id": "open_source", "label": "Open Source", "icon": "open", "enabled": true, "danger": false }
        ]
    }

    readonly property var _inboxRows: root._buildInboxRows(root.inboxPanelModel.items || [])
    readonly property var _mentionRows: root._buildMentionRows(root.mentionsPanelModel.items || [])
    readonly property var _approvalRows: root._buildApprovalRows(root.approvalsPanelModel.items || [])
    readonly property var _activityFeedItems: root._filterFeedItems(root.activityPanelModel.items || [], root.activitySearchText)
    readonly property var _teamUpdateRows: root._buildTeamUpdateRows(root.teamUpdatesPanelModel.items || [])
    readonly property var _auditFeedItems: root._filterFeedItems(root.auditPanelModel.items || [], root.auditSearchText)

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    function _rowById(rowId, rows) {
        const list = rows || []
        for (let i = 0; i < list.length; i += 1) {
            if (String(list[i].id || "") === String(rowId || "")) {
                return list[i]
            }
        }
        return null
    }

    function _panelSearchText(panelId) {
        if (panelId === "mentions") return root.mentionsSearchText
        if (panelId === "approvals") return root.approvalsSearchText
        if (panelId === "activity") return root.activitySearchText
        if (panelId === "team_updates") return root.teamUpdatesSearchText
        if (panelId === "audit") return root.auditSearchText
        return root.inboxSearchText
    }

    function _setPanelSearchText(panelId, text) {
        if (panelId === "mentions") root.mentionsSearchText = text
        else if (panelId === "approvals") root.approvalsSearchText = text
        else if (panelId === "activity") root.activitySearchText = text
        else if (panelId === "team_updates") root.teamUpdatesSearchText = text
        else if (panelId === "audit") root.auditSearchText = text
        else root.inboxSearchText = text
        root._resetPanelPage(panelId)
    }

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

    function _resetPanelPage(panelId) {
        root._setPanelPage(panelId, 1)
    }

    function _resetAllTablePages() {
        root.inboxPage = 1
        root.mentionsPage = 1
        root.approvalsPage = 1
        root.teamUpdatesPage = 1
    }

    function _formatTitleCase(value) {
        const raw = String(value || "").replace(/_/g, " ").trim()
        if (raw.length === 0) {
            return ""
        }
        const words = raw.split(" ")
        for (let i = 0; i < words.length; i += 1) {
            const word = String(words[i] || "")
            if (word.length > 0) {
                words[i] = word.charAt(0).toUpperCase() + word.slice(1)
            }
        }
        return words.join(" ")
    }

    function _matchesGlobalFilters(item) {
        const state = item && item.state ? item.state : {}
        if (root.selectedProjectId !== "all" && String(state.projectId || "") !== String(root.selectedProjectId || "")) {
            return false
        }
        const teamKey = String(
            state.actorUsername || state.requestor || state.username || ""
        )
        if (root.selectedTeamId !== "all" && teamKey !== String(root.selectedTeamId || "")) {
            return false
        }
        if (root.selectedUnreadKey === "unread" && !Boolean(state.unread)) {
            return false
        }
        if (root.selectedUnreadKey === "attention" && !Boolean(state.attention)) {
            return false
        }
        if (root.selectedPeriodKey !== "all") {
            const createdAt = String(state.createdAt || "")
            if (!root._matchesPeriod(createdAt)) {
                return false
            }
        }
        return true
    }

    function _matchesPeriod(createdAtIso) {
        if (!createdAtIso || root.selectedPeriodKey === "all") {
            return true
        }
        const observed = new Date(createdAtIso)
        if (isNaN(observed.getTime())) {
            return true
        }
        const now = new Date()
        const deltaMs = now.getTime() - observed.getTime()
        if (root.selectedPeriodKey === "24h") return deltaMs <= 24 * 60 * 60 * 1000
        if (root.selectedPeriodKey === "7d") return deltaMs <= 7 * 24 * 60 * 60 * 1000
        if (root.selectedPeriodKey === "30d") return deltaMs <= 30 * 24 * 60 * 60 * 1000
        return true
    }

    function _matchesSearch(item, searchText) {
        const query = String(searchText || "").trim().toLowerCase()
        if (query.length === 0) {
            return true
        }
        const haystack = [
            item.title,
            item.subtitle,
            item.supportingText,
            item.metaText,
            item.statusLabel
        ].join(" ").toLowerCase()
        return haystack.indexOf(query) >= 0
    }

    function _buildInboxRows(items) {
        const rows = []
        const list = items || []
        for (let i = 0; i < list.length; i += 1) {
            const item = list[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.inboxSearchText)) {
                continue
            }
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "title": item.title,
                "workflowType": root._formatTitleCase(state.notificationType || "workflow"),
                "projectName": state.projectName || "Cross-project",
                "supportingText": item.supportingText || "",
                "statusLabel": item.statusLabel || "",
                "subtitle": item.subtitle || "",
                "metaText": item.metaText || "",
                "state": state
            })
        }
        return rows
    }

    function _buildMentionRows(items) {
        const rows = []
        const list = items || []
        for (let i = 0; i < list.length; i += 1) {
            const item = list[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.mentionsSearchText)) {
                continue
            }
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "title": item.title,
                "sourceName": state.taskId || item.subtitle || "",
                "actorLabel": state.actorUsername ? ("@" + state.actorUsername) : "",
                "metaText": item.metaText || "",
                "statusLabel": item.statusLabel || "",
                "subtitle": item.subtitle || "",
                "supportingText": item.supportingText || "",
                "state": state
            })
        }
        return rows
    }

    function _buildApprovalRows(items) {
        const rows = []
        const list = items || []
        for (let i = 0; i < list.length; i += 1) {
            const item = list[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.approvalsSearchText)) {
                continue
            }
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "title": item.title,
                "approvalType": root._formatTitleCase(state.requestType || state.entityType || "approval"),
                "requestor": state.requestor ? ("@" + state.requestor) : "",
                "moduleLabel": state.moduleLabel || "",
                "statusLabel": item.statusLabel || "",
                "subtitle": item.subtitle || "",
                "supportingText": item.supportingText || "",
                "metaText": item.metaText || "",
                "state": state
            })
        }
        return rows
    }

    function _buildTeamUpdateRows(items) {
        const rows = []
        const list = items || []
        for (let i = 0; i < list.length; i += 1) {
            const item = list[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, root.teamUpdatesSearchText)) {
                continue
            }
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "title": item.title,
                "activityType": item.statusLabel || "",
                "sourceName": state.taskName || item.subtitle || "",
                "projectName": state.projectName || "",
                "metaText": item.supportingText || "",
                "subtitle": item.subtitle || "",
                "supportingText": item.supportingText || "",
                "statusLabel": item.statusLabel || "",
                "state": state
            })
        }
        return rows
    }

    function _filterFeedItems(items, searchText) {
        const list = []
        const source = items || []
        for (let i = 0; i < source.length; i += 1) {
            const item = source[i]
            if (!root._matchesGlobalFilters(item) || !root._matchesSearch(item, searchText)) {
                continue
            }
            list.push(item)
        }
        return list
    }

    function _clearFilters() {
        root.selectedProjectId = "all"
        root.selectedTeamId = "all"
        root.selectedPeriodKey = "all"
        root.selectedUnreadKey = "all"
        root._resetAllTablePages()
    }

    function _openRow(panelId, rowId) {
        root._selectedRowId = String(rowId || "")
        if (root.workspaceController !== null && root._selectedRowId.length > 0) {
            root.workspaceController.selectItem(panelId, root._selectedRowId)
        }
    }

    function _navigateRoute(routeId) {
        if (root.shellModel && String(routeId || "").length > 0) {
            root.shellModel.selectRoute(String(routeId || ""))
        }
    }

    function _handleCurrentAction(actionId) {
        const item = root._selectedRowItem
        if (!item || root.workspaceController === null) {
            return
        }
        const state = item.state || {}
        if (actionId === "mark_read") {
            root.workspaceController.markItemRead(root.activePanelId, item.id)
        } else if (actionId === "approve") {
            root.workspaceController.approveRequest(String(state.requestId || ""))
        } else if (actionId === "reject") {
            root.workspaceController.rejectRequest(String(state.requestId || ""))
        } else if (actionId === "open_source") {
            root._navigateRoute(String(state.routeId || ""))
        }
    }

    function _handleDetailAction(actionId) {
        const state = root.selectedDetailModel.state || {}
        if (actionId === "back") {
            root.workspaceController.clearSelection()
            root._selectedRowId = ""
            return
        }
        if (actionId === "mark_read") {
            root.workspaceController.markItemRead(
                String(state.panelId || root.activePanelId),
                String(root.selectedDetailModel.id || "")
            )
            return
        }
        if (actionId === "approve") {
            root.workspaceController.approveRequest(String(state.requestId || ""))
            return
        }
        if (actionId === "reject") {
            root.workspaceController.rejectRequest(String(state.requestId || ""))
            return
        }
        if (actionId === "open_source") {
            root._navigateRoute(String(state.routeId || ""))
        }
    }

    function _detailActions() {
        const state = root.selectedDetailModel.state || {}
        const panelId = String(state.panelId || root.activePanelId)
        if (panelId === "approvals") {
            const pending = String(state.status || "").toLowerCase() === "pending"
            return [
                { "id": "approve", "label": "Approve", "icon": "approve", "enabled": pending, "danger": false },
                { "id": "reject", "label": "Reject", "icon": "close", "enabled": pending, "danger": true },
                { "id": "open_source", "label": "Open Source", "icon": "open", "enabled": true, "danger": false }
            ]
        }
        const canMarkRead = !!(state.taskId)
        return [
            { "id": "mark_read", "label": "Mark Read", "icon": "approve", "enabled": canMarkRead, "danger": false },
            { "id": "open_source", "label": "Open Source", "icon": "open", "enabled": true, "danger": false }
        ]
    }

    onActivePanelIdChanged: {
        root._selectedRowId = ""
        root._resetPanelPage(root.activePanelId)
        if (root.workspaceController !== null) {
            root.workspaceController.clearSelection()
        }
    }

    onSelectedProjectIdChanged: root._resetAllTablePages()
    onSelectedTeamIdChanged: root._resetAllTablePages()
    onSelectedPeriodKeyChanged: root._resetAllTablePages()
    onSelectedUnreadKeyChanged: root._resetAllTablePages()

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        CollaborationToolbarSection {
            id: contextToolbar
            Layout.fillWidth: true
            contextModel: root.contextModel
            selectedProjectId: root.selectedProjectId
            selectedTeamId: root.selectedTeamId
            selectedPeriodKey: root.selectedPeriodKey
            selectedUnreadKey: root.selectedUnreadKey
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            onProjectChanged: function(value) { root.selectedProjectId = value }
            onTeamChanged: function(value) { root.selectedTeamId = value }
            onPeriodChanged: function(value) { root.selectedPeriodKey = value }
            onUnreadChanged: function(value) { root.selectedUnreadKey = value }
            onRefreshRequested: function() {
                if (root.workspaceController !== null) {
                    root.workspaceController.refresh()
                }
            }
            onSettingsRequested: settingsPopup.open()
        }

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "info"
            message: root.workspaceController && root.workspaceController.isBusy
                ? "Updating collaboration workflows..."
                : "Loading collaboration workspace..."
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

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
                        required property var modelData
                        width: _tabRow.implicitWidth + 18
                        height: parent.height

                        readonly property bool _active: String(modelData.id || "") === root.activePanelId

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.AppTheme.radiusSm
                            color: _active
                                ? Theme.AppTheme.navSelectedBackground
                                : (_tabHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent")
                        }

                        Row {
                            id: _tabRow
                            anchors.centerIn: parent
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                text: String(modelData.label || "")
                                color: _active ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: _active
                            }

                            Rectangle {
                                visible: Number(modelData.count || 0) > 0
                                width: _countLabel.implicitWidth + 10
                                height: 18
                                radius: 9
                                color: _active ? Theme.AppTheme.accent : Theme.AppTheme.surfaceOverlay

                                AppControls.Label {
                                    id: _countLabel
                                    anchors.centerIn: parent
                                    text: String(modelData.count || 0)
                                    color: _active ? Theme.AppTheme.textOnAccent : Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }
                        }

                        HoverHandler { id: _tabHover }

                        TapHandler {
                            onTapped: root.activePanelId = String(modelData.id || "inbox")
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                anchors.fill: parent
                visible: !root._detailOpen || detailPageLoader.status !== Loader.Ready
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceRaised
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        title: root._selectedRowItem
                            ? String(root._selectedRowItem.title || "")
                            : String(root._currentPanelModel.title || "")
                        subtitle: root._selectedRowItem
                            ? String(root._selectedRowItem.subtitle || root._selectedRowItem.supportingText || "")
                            : String(root._currentPanelModel.subtitle || "")
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: root._currentContextActions
                        onActionTriggered: function(actionId) {
                            root._handleCurrentAction(actionId)
                        }
                    }

                    AppWidgets.TableToolbar {
                        id: panelToolbar
                        Layout.fillWidth: true
                        searchText: root._panelSearchText(root.activePanelId)
                        searchPlaceholder: {
                            if (root.activePanelId === "mentions") return "Search mentions..."
                            if (root.activePanelId === "approvals") return "Search approvals..."
                            if (root.activePanelId === "team_updates") return "Search team updates..."
                            if (root.activePanelId === "activity") return "Search activity..."
                            if (root.activePanelId === "audit") return "Search audit..."
                            return "Search inbox..."
                        }
                        showFilter: true
                        showViews: true
                        showCustomize: root.activePanelId !== "activity" && root.activePanelId !== "audit"
                        showExport: true
                        showRefresh: true
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                        onSearchChanged: function(text) {
                            root._setPanelSearchText(root.activePanelId, text)
                        }
                        onFilterClicked: {
                            panelFilterPopup.anchorItem = panelToolbar.filterButtonItem
                            panelFilterPopup.open()
                        }
                        onViewsClicked: {
                            panelViewsPopup.anchorItem = panelToolbar.viewsButtonItem
                            panelViewsPopup.open()
                        }
                        onCustomizeClicked: {
                            if (root.activePanelId !== "activity" && root.activePanelId !== "audit") {
                                panelTable.openColumnCustomizer(panelToolbar.customizeButtonItem)
                            }
                        }
                        onRefreshRequested: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.refresh()
                            }
                        }
                        onExportRequested: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.exportPanel(root.activePanelId)
                            }
                        }
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
                            visible: root.activePanelId !== "activity" && root.activePanelId !== "audit"
                            columns: root._currentTableColumns
                            selectedRowId: root._selectedRowId
                            emptyText: root._currentPanelModel.emptyState || "No collaboration items are available."
                            loading: root.workspaceController ? root.workspaceController.isLoading : false
                            onRowSelected: function(rowId) {
                                root._selectedRowId = rowId
                            }
                            onRowActivated: function(rowId) {
                                root._openRow(root.activePanelId, rowId)
                            }
                        }

                        AppWidgets.TablePaginationBar {
                            id: paginationBar
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            visible: root.activePanelId !== "activity" && root.activePanelId !== "audit"
                            currentPage: root._effectiveTablePage
                            pageSize: root._currentTablePageSize
                            totalItems: root._currentTableTotalItems
                            busy: root.workspaceController
                                ? (root.workspaceController.isBusy || root.workspaceController.isLoading)
                                : false

                            onPageRequested: function(page) {
                                root._setPanelPage(root.activePanelId, page)
                            }
                            onPageSizeRequested: function(pageSize) {
                                root._setPanelPageSize(root.activePanelId, pageSize)
                            }
                        }

                        ScrollView {
                            anchors.fill: parent
                            visible: root.activePanelId === "activity" || root.activePanelId === "audit"
                            contentWidth: availableWidth
                            clip: true

                            ColumnLayout {
                                width: parent.width
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.ActivityFeed {
                                    Layout.fillWidth: true
                                    items: root.activePanelId === "activity"
                                        ? root._activityFeedItems
                                        : root._auditFeedItems
                                    emptyText: root._currentPanelModel.emptyState || "No collaboration activity is available."
                                    onItemActivated: function(itemData) {
                                        const state = itemData && itemData.state ? itemData.state : {}
                                        root._navigateRoute(String(state.routeId || ""))
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Loader {
                id: detailPageLoader
                anchors.fill: parent
                active: root._detailOpen
                visible: root._detailOpen && status === Loader.Ready
                asynchronous: true
                sourceComponent: Component {
                    AppWidgets.SectionDetailPage {
                        id: detailPage
                        anchors.fill: parent
                        open: true
                        title: root.selectedDetailModel.title || "Collaboration Item"
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                        showEdit: false
                        showDelete: false
                        sections: [
                            "Overview",
                            "Activity",
                            "Related Items",
                            "Audit"
                        ]
                        onBackRequested: root._handleDetailAction("back")

                        ColumnLayout {
                            width: parent.width
                            spacing: 0

                            AppWidgets.ContextualActionToolbar {
                                Layout.fillWidth: true
                                showBack: true
                                title: root.selectedDetailModel.title || "Workflow Item"
                                subtitle: root.selectedDetailModel.statusLabel || root.selectedDetailModel.subtitle || ""
                                busy: root.workspaceController ? root.workspaceController.isBusy : false
                                actions: root._detailActions()
                                onBackRequested: root._handleDetailAction("back")
                                onActionTriggered: function(actionId) {
                                    root._handleDetailAction(actionId)
                                }
                            }

                            CollaborationDetailPanel {
                                Layout.fillWidth: true
                                detailModel: root.selectedDetailModel
                                detailPage: detailPage
                                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                onRelatedItemActivated: function(itemData) {
                                    const state = itemData && itemData.state ? itemData.state : {}
                                    root._navigateRoute(String(state.routeId || ""))
                                }
                                onActivityItemActivated: function(itemData) {
                                    const state = itemData && itemData.state ? itemData.state : {}
                                    root._navigateRoute(String(state.routeId || ""))
                                }
                                onAuditItemActivated: function(itemData) {
                                    const state = itemData && itemData.state ? itemData.state : {}
                                    root._navigateRoute(String(state.routeId || ""))
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.AnchoredPopup {
        id: panelFilterPopup
        width: 280
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: Theme.AppTheme.dialogPadding
        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.dialogBackground
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        ColumnLayout {
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                Layout.fillWidth: true
                text: "Active Filters"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Use the collaboration context toolbar to change project, team, period, and unread scope for all panels."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.SecondaryButton {
                text: "Clear Filters"
                iconName: "close"
                onClicked: {
                    root._clearFilters()
                    panelFilterPopup.close()
                }
            }

            AppControls.PrimaryButton {
                text: "Apply View"
                iconName: "approve"
                onClicked: panelFilterPopup.close()
            }
        }
    }

    AppWidgets.AnchoredPopup {
        id: panelViewsPopup
        width: 240
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: Theme.AppTheme.dialogPadding
        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.dialogBackground
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        ColumnLayout {
            width: parent.width
            spacing: Theme.AppTheme.spacingSm

            Repeater {
                model: [
                    { "label": "Operational Inbox", "panelId": "inbox", "unread": "all" },
                    { "label": "Mentions Focus", "panelId": "mentions", "unread": "unread" },
                    { "label": "Pending Approvals", "panelId": "approvals", "unread": "attention" },
                    { "label": "Activity Journal", "panelId": "activity", "unread": "all" },
                    { "label": "Team Updates", "panelId": "team_updates", "unread": "all" },
                    { "label": "Audit Trail", "panelId": "audit", "unread": "all" }
                ]

                delegate: AppControls.SecondaryButton {
                    required property var modelData
                    Layout.fillWidth: true
                    text: String(modelData.label || "")
                    onClicked: {
                        root.activePanelId = String(modelData.panelId || "inbox")
                        root.selectedUnreadKey = String(modelData.unread || "all")
                        panelViewsPopup.close()
                    }
                }
            }
        }
    }

    AppWidgets.AnchoredPopup {
        id: settingsPopup
        width: 280
        modal: false
        focus: true
        anchorItem: contextToolbar.settingsButtonItem
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: Theme.AppTheme.dialogPadding
        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.dialogBackground
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        ColumnLayout {
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                Layout.fillWidth: true
                text: "Collaboration Settings"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Panel-specific notification preferences and saved workflow views can be added here in the next iteration."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.PrimaryButton {
                text: "Close"
                iconName: "approve"
                onClicked: settingsPopup.close()
            }
        }
    }
}
