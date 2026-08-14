pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents

// R5.2: Roles & Access, normalized into the same list -> inspector -> detail
// model as every other entity (design doc §9). Replaces the old
// AccessSecurityPanel's three simultaneous interaction mechanisms (inline
// assignment form, inline 272px grant inspector, separate detail page) with:
//   - AdminEntityWorkspace (list) + InspectorPanel (single-click) -- same
//     shared components every other R4/R5 entity uses.
//   - "Assign Access" as an EntityDialog, not a permanently-visible form.
//   - The existing AdminAccessDetailPage, unchanged, opened via "Open"/double-click.
// Revoke Access / Revoke Sessions / Force Password Reset now go through
// ConfirmationDialog (built in R1, never wired into Platform until now) per
// D5's deactivate-style policy -- these had NO confirmation at all before.
// Account Security & Sessions stays a separate table, unchanged in shape,
// exactly as the doc specifies (it's a different entity -- sessions, not
// grants -- and wasn't part of the triplication problem).
// access_workspace_controller.py / access_workspace_presenter.py are NOT
// modified -- this is QML-layer normalization only.
AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminAccessWorkspaceController controller: root.platformCatalog
        ? root.platformCatalog.adminAccessWorkspace
        : null

    signal navigateToDestination(string destinationId)

    function openRecord(rowId) {
        root.selectedGrantId = String(rowId || "")
        root.detailOpen = root.selectedGrantId.length > 0
    }

    property var grantsCatalog: root.controller
        ? root.controller.scopeGrants
        : ({ "title": "Roles & Access", "subtitle": "", "emptyState": "", "items": [] })
    property var sessionsCatalog: root.controller
        ? root.controller.securityUsers
        : ({ "title": "Account Security & Sessions", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _grantColumns: [
        { key: "title",       label: "Principal", flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Username",  flex: 2, minWidth: 110, sortable: false, visible: true },
        { key: "statusLabel", label: "Role",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Assigned",  flex: 2, minWidth: 130, sortable: false, visible: true, hideBelow: Theme.AppTheme.compactContentBreakpoint }
    ]
    readonly property var _sessionColumns: [
        { key: "title",          label: "User",     flex: 2, minWidth: 120, sortable: true,  visible: true },
        { key: "subtitle",       label: "Username", flex: 2, minWidth: 100, sortable: false, visible: true },
        { key: "statusLabel",    label: "Status",   flex: 0, minWidth: 80,  sortable: false, visible: true, type: "status" },
        { key: "supportingText", label: "Posture",  flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "metaText",       label: "Details",  flex: 3, minWidth: 200, sortable: false, visible: true }
    ]

    property string selectedGrantId: ""
    property bool detailOpen: false
    property string selectedSessionId: ""
    // Top-level split: "Scope Access" (grants) vs "Account Security"
    // (sessions) -- previously both were always shown stacked on one page.
    property string activePanel: "scope"

    readonly property bool   busy: root.controller ? root.controller.isBusy          : false
    readonly property bool   load: root.controller ? root.controller.isLoading       : false
    readonly property string err:  root.controller ? root.controller.errorMessage    : ""
    readonly property string ok:   root.controller ? root.controller.feedbackMessage : ""

    readonly property var _selectedGrantItem: {
        const id = root.selectedGrantId
        if (!id) return null
        const items = root.grantsCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _selectedSessionItem: {
        const id = root.selectedSessionId
        if (!id) return null
        const items = root.sessionsCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _grantInspectorSections: {
        const item = root._selectedGrantItem
        if (!item) return []
        return [
            { "label": "Username", "value": String(item.subtitle || "") },
            { "label": "Permissions", "value": String(item.supportingText || "") },
            { "label": "Assigned", "value": String(item.metaText || "") }
        ]
    }

    readonly property var _sessionActions: {
        const item = root._selectedSessionItem
        if (!item) return []
        const acts = []
        if (item.canPrimaryAction)
            acts.push({ id: "unlock", label: "Unlock Account", icon: "approve", enabled: true, danger: false })
        if (item.canSecondaryAction)
            acts.push({ id: "revoke", label: "Revoke Sessions", icon: "delete", enabled: true, danger: true })
        acts.push({ id: "force_reset", label: "Force Password Reset", icon: "edit", enabled: true, danger: false })
        return acts
    }

    function indexOfOption(options, value) {
        for (let i = 0; i < options.length; i += 1) {
            if ((options[i].value || "") === value) return i
        }
        return options.length > 0 ? 0 : -1
    }

    function optionValue(options, index) {
        if (index < 0 || index >= options.length) return ""
        return options[index].value || ""
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.controller) root.controller.clearMessages()
    }

    // -- Confirmation dispatch (Revoke Access / Revoke Sessions / Force
    // Password Reset all funnel through one shared ConfirmationDialog,
    // matching D5's deactivate-style policy for security-consequential
    // actions -- none of these had any confirmation before this phase.
    property var _pendingConfirm: null

    function requestRevokeGrant(grantItem) {
        if (!grantItem) return
        root._pendingConfirm = {
            "type": "revoke_grant",
            "userId": String(grantItem.id || ""),
            "message": "Revoke access for " + String(grantItem.title || "this principal") + "?",
            "supportingText": "They will immediately lose the \"" + String(grantItem.statusLabel || "") + "\" role at this scope.",
            "confirmLabel": "Revoke Access"
        }
        confirmDialog.open()
    }

    function requestRevokeSessions(sessionItem) {
        if (!sessionItem) return
        root._pendingConfirm = {
            "type": "revoke_sessions",
            "userId": String(sessionItem.id || ""),
            "message": "Revoke all active sessions for " + String(sessionItem.title || "this user") + "?",
            "supportingText": "They will be signed out everywhere and must sign in again.",
            "confirmLabel": "Revoke Sessions"
        }
        confirmDialog.open()
    }

    function requestForcePasswordReset(sessionItem) {
        if (!sessionItem) return
        root._pendingConfirm = {
            "type": "force_reset",
            "userId": String(sessionItem.id || ""),
            "message": "Force a password reset for " + String(sessionItem.title || "this user") + "?",
            "supportingText": "They will be required to set a new password before their next sign-in.",
            "confirmLabel": "Force Password Reset"
        }
        confirmDialog.open()
    }

    title: "Roles & Access"

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.sectionGap
        visible: !root.detailOpen

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.err.length > 0
            tone: "danger"
            message: root.err
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.ok.length > 0 && root.err.length === 0
            tone: "success"
            message: root.ok
        }

        // ── Panel tab bar: Scope Access vs Account Security ───────────
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
                        { id: "scope",    label: "Scope Access",     count: (root.grantsCatalog.items || []).length },
                        { id: "security", label: "Account Security", count: (root.sessionsCatalog.items || []).length }
                    ]

                    delegate: Item {
                        id: _tab
                        required property var modelData
                        readonly property bool _active: root.activePanel === _tab.modelData.id

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
                                root.activePanel = _tab.modelData.id
                                root.selectedGrantId = ""
                                root.selectedSessionId = ""
                            }
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.activePanel === "scope"
            spacing: 0

            PlatformComponents.AdminEntityWorkspace {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Scoped Access Grants"
                entityLabel: "Access"
                catalog: root.grantsCatalog
                catalogModel: root.controller ? root.controller.scopeGrantsTableModel : null
                columns: root._grantColumns
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedGrantId

                onCreateRequested: assignDialog.open()
                onRowSelected: function(id) { root.selectedGrantId = id }
                onRowActivated: function(id) { root.selectedGrantId = id; root.detailOpen = true }
                onRefreshRequested: { if (root.controller) root.controller.refresh() }
            }

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                visible: root.selectedGrantId.length > 0 && Window.width >= Theme.AppTheme.compactContentBreakpoint
                title: root._selectedGrantItem ? String(root._selectedGrantItem.title || "") : ""
                statusLabel: root._selectedGrantItem ? String(root._selectedGrantItem.statusLabel || "") : ""
                sections: root._grantInspectorSections
                busy: root.busy
                editActionLabel: "Open"
                showEditAction: true
                secondaryActionLabel: "Revoke Access"
                showSecondaryAction: true

                onCloseRequested: root.selectedGrantId = ""
                onEditRequested: root.detailOpen = true
                onSecondaryActionRequested: root.requestRevokeGrant(root._selectedGrantItem)
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.activePanel === "security"
            spacing: Theme.AppTheme.sectionGap

            AppWidgets.TableToolbar {
                id: _securityToolbar
                Layout.fillWidth: true
                searchPlaceholder: "Search security records..."
                showCustomize: true
                showRefresh: true
                isBusy: root.busy
                onRefreshRequested: { if (root.controller) root.controller.refresh() }
                onCustomizeClicked: _securityTable.openColumnCustomizer(_securityToolbar.customizeButtonItem)
            }

            AppWidgets.ContextualActionToolbar {
                Layout.fillWidth: true
                visible: root._selectedSessionItem !== null
                title: root._selectedSessionItem ? String(root._selectedSessionItem.title || "") : ""
                subtitle: root._selectedSessionItem ? String(root._selectedSessionItem.supportingText || "") : ""
                busy: root.busy
                actions: root._sessionActions
                onActionTriggered: function(actionId) {
                    const item = root._selectedSessionItem
                    if (!root.controller || !item) return
                    if (actionId === "unlock") root.controller.unlockUser(item.id || "")
                    else if (actionId === "revoke") root.requestRevokeSessions(item)
                    else if (actionId === "force_reset") root.requestForcePasswordReset(item)
                }
            }

            AppWidgets.DataTable {
                id: _securityTable
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceModel: root.controller ? root.controller.securityUsersTableModel : null
                columns: root._sessionColumns
                emptyText: root.controller ? (root.sessionsCatalog.emptyState || "No security records") : "No security records"
                selectedRowId: root.selectedSessionId
                onRowSelected: function(rowId) { root.selectedSessionId = rowId }
                onRowActivated: function(rowId) { root.selectedSessionId = rowId }
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: root.detailOpen
        visible: active
        asynchronous: true

        sourceComponent: Component {
            AdminAccessDetailPage {
                controller: root.controller
                grantId: root.selectedGrantId
                busy: root.busy
                errorMessage: root.err
                feedbackMessage: root.ok
                onBackRequested: root.closeDetail()
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: confirmDialog
        title: root._pendingConfirm ? String(root._pendingConfirm.confirmLabel || "Confirm") : "Confirm"
        confirmLabel: root._pendingConfirm ? String(root._pendingConfirm.confirmLabel || "Confirm") : "Confirm"
        confirmIcon: "delete"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""

        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.controller) return
            if (pending.type === "revoke_grant") {
                root.controller.removeMembership(pending.userId)
                root.selectedGrantId = ""
            } else if (pending.type === "revoke_sessions") {
                root.controller.revokeSessions(pending.userId)
            } else if (pending.type === "force_reset") {
                root.controller.forcePasswordReset(pending.userId)
            }
            root._pendingConfirm = null
        }
    }

    AppWidgets.EntityDialog {
        id: assignDialog
        title: "Assign Access"
        subtitle: "Grant a principal a role at a chosen scope."
        errorMessage: root.err
        primaryText: "Assign Access"
        primaryIcon: "approve"

        function submitDialog() {
            if (!root.controller) return
            const result = root.controller.assignMembership()
            if (!result || result.ok === false) {
                assignDialog.errorMessage = String((result && result.message) || "Operation failed. Please try again.")
            } else {
                assignDialog.errorMessage = ""
                assignDialog.close()
            }
        }

        onRejected: assignDialog.close()

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: Theme.AppTheme.spacingLg
            rowSpacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Scope Type" }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    enabled: root.controller ? !root.controller.isBusy : false
                    model: root.controller ? root.controller.scopeTypeOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller ? root.controller.scopeTypeOptions : [],
                        root.controller ? root.controller.selectedScopeType : ""
                    )
                    onActivated: {
                        if (root.controller)
                            root.controller.setScopeType(root.optionValue(root.controller.scopeTypeOptions, currentIndex))
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Scope" }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    enabled: root.controller ? !root.controller.isBusy : false
                    model: root.controller ? root.controller.scopeOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller ? root.controller.scopeOptions : [],
                        root.controller ? root.controller.selectedScopeId : ""
                    )
                    onActivated: {
                        if (root.controller)
                            root.controller.setScopeId(root.optionValue(root.controller.scopeOptions, currentIndex))
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Principal" }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    enabled: root.controller ? !root.controller.isBusy : false
                    model: root.controller ? root.controller.userOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller ? root.controller.userOptions : [],
                        root.controller ? root.controller.selectedUserId : ""
                    )
                    onActivated: {
                        if (root.controller)
                            root.controller.setSelectedUserId(root.optionValue(root.controller.userOptions, currentIndex))
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Role" }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    enabled: root.controller ? !root.controller.isBusy : false
                    model: root.controller ? root.controller.roleOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller ? root.controller.roleOptions : [],
                        root.controller ? root.controller.selectedRole : ""
                    )
                    onActivated: {
                        if (root.controller)
                            root.controller.setSelectedRole(root.optionValue(root.controller.roleOptions, currentIndex))
                    }
                }
            }

            AppControls.Label {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                visible: text.length > 0
                text: root.controller ? root.controller.scopeHint : ""
                color: Theme.AppTheme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
    }
}
