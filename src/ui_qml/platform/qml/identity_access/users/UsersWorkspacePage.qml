pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import App.Theme 1.0 as Theme
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents
import Platform.Dialogs 1.0 as AdminDialogs
import App.Controls 1.0 as AppControls

// R5: Users as a standalone Platform destination -- same shape as R4's
// Organizations/Sites/etc. pages (AdminEntityWorkspace + InspectorPanel +
// existing unchanged AdminUserDetailPage + shared AdminDialogHost).
AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null
    property PlatformControllers.PlatformSettingsWorkspaceController settingsController: root.platformCatalog
        ? root.platformCatalog.settingsWorkspace
        : null

    signal navigateToDestination(string destinationId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var userCatalog: root.workspaceController
        ? root.workspaceController.users
        : ({ "title": "Users", "subtitle": "", "emptyState": "", "items": [] })
    property var moduleEntitlementCatalog: root.settingsController
        ? root.settingsController.moduleEntitlements
        : ({ "title": "Module Entitlements", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _columns: [
        { key: "title",       label: "Display Name", flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Username",     flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",       flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Security",     flex: 3, minWidth: 180, sortable: false, visible: true, hideBelow: Theme.AppTheme.compactContentBreakpoint }
    ]
    readonly property var _moduleColumns: [
        { key: "title",       label: "Module",          flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Stage / License", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Lifecycle",       flex: 0, minWidth: 100, sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Runtime",         flex: 3, minWidth: 200, sortable: false, visible: true }
    ]

    property string selectedRowId: ""
    property bool detailOpen: false
    property var _pendingConfirm: null

    // RBAC: gates create/edit/activate-toggle buttons -- a client-side UX
    // optimization mirroring PlatformNavigation's own destination gate;
    // the backend enforces "auth.manage" independently regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("auth.manage")
        : true

    function requestToggleActive() {
        const item = root._selectedItem
        if (!item || !root.workspaceController) return
        if (item.isActive) {
            root._pendingConfirm = {
                "itemId": root.selectedRowId,
                "message": "Deactivate " + String(item.title || "this user") + "?",
                "supportingText": "They will lose access to assigned projects."
            }
            confirmDialog.open()
        } else {
            root.workspaceController.toggleUserActive(root.selectedRowId)
        }
    }

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.userCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _inspectorSections: {
        const item = root._selectedItem
        if (!item) return []
        return [
            { "label": "Details", "value": String(item.subtitle || "") },
            { "label": "Info", "value": String(item.metaText || "") }
        ]
    }

    function _itemById(itemId) {
        const items = root.userCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openUserEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    function handleDetailAction(actionId) {
        const id = root.selectedRowId
        if (actionId === "edit") { root.openEdit(id); return }
        if (actionId === "toggle_active" && root.workspaceController) { root.requestToggleActive(); return }
        if (actionId === "refresh") { if (root.workspaceController) root.workspaceController.refresh(); return }
        if (actionId === "show_access") { root.navigateToDestination("access"); return }
        if (actionId === "show_audit") { root.navigateToDestination("control_audit"); return }
    }

    title: "Users"
    subtitle: String(root.userCatalog.subtitle || "")

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0
            visible: !root.detailOpen

            PlatformComponents.AdminEntityWorkspace {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Users"
                entityLabel: "User"
                catalog: root.userCatalog
                catalogModel: root.workspaceController ? root.workspaceController.usersTableModel : null
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId

                onCreateRequested: dialogHostLoader.invoke("openUserCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                visible: root.selectedRowId.length > 0 && Window.width >= Theme.AppTheme.compactContentBreakpoint
                title: root._selectedItem ? String(root._selectedItem.title || "") : ""
                statusLabel: root._selectedItem ? String(root._selectedItem.statusLabel || "") : ""
                sections: root._inspectorSections
                busy: root.busy
                editActionLabel: "Edit"
                showEditAction: root._canWrite
                secondaryActionLabel: root._selectedItem && root._selectedItem.isActive ? "Deactivate" : "Activate"
                showSecondaryAction: root._canWrite

                onCloseRequested: root.selectedRowId = ""
                onEditRequested: root.openEdit(root.selectedRowId)
                onSecondaryActionRequested: root.requestToggleActive()
            }
        }

        Loader {
            anchors.fill: parent
            active: root.detailOpen
            visible: active
            asynchronous: true

            sourceComponent: Component {
                AdminUserDetailPage {
                    user: root._selectedItem || ({})
                    canWrite: root._canWrite
                    moduleEntitlementCatalog: root.moduleEntitlementCatalog
                    moduleEntitlementColumns: root._moduleColumns
                    busy: root.busy
                    errorMessage: root.err
                    feedbackMessage: root.ok

                    onBackRequested: root.closeDetail()
                    onActionRequested: function(actionId) { root.handleDetailAction(actionId) }
                }
            }
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            AdminDialogs.AdminDialogHost {
                workspaceController: root.workspaceController
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: confirmDialog
        title: "Confirm"
        confirmLabel: "Deactivate"
        confirmIcon: "delete"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            root.workspaceController.toggleUserActive(pending.itemId)
            root._pendingConfirm = null
        }
    }
}
