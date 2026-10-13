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
import "sections/PartiesColumnConfig.js" as ColumnConfig

// Parties as a standalone Platform destination. Same shape as
// EmployeesWorkspacePage/DepartmentsWorkspacePage: server-side pagination/
// search/status filter/Columns, plus Type and Role filters (Party's own
// identity-axis and multi-valued business-role set). No calendar
// assignment, no related-record list -- Party has no natural hierarchy
// parent in Platform.
AppLayouts.WorkspaceFrame {
    id: root
    objectName: "partiesWorkspacePage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    signal navigateToDestination(string destinationId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var partyCatalog: root.workspaceController
        ? root.workspaceController.parties
        : ({ "title": "Parties", "subtitle": "", "emptyState": "", "items": [] })

    readonly property string _tableId: "platform.parties.table"
    property var _columns: []

    function _initializeColumns() {
        const base = ColumnConfig.baseColumns(Theme.AppTheme.compactContentBreakpoint)
        const saved = root.workspaceController !== null
            ? root.workspaceController.loadTableColumnState(root._tableId)
            : ({})
        root._columns = ColumnConfig.applyColumnState(base, saved)
    }

    function _saveColumnState(newColumns) {
        if (root.workspaceController !== null) {
            root.workspaceController.saveTableColumnState(
                root._tableId,
                ColumnConfig.buildColumnState(newColumns)
            )
        }
        root._columns = newColumns
    }

    Component.onCompleted: root._initializeColumns()

    // Party lifecycle is a plain 2-state Active/Inactive (PartyLifecycleStatus).
    readonly property var _statusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _typeFilterOptions: {
        const options = root.workspaceController ? (root.workspaceController.partyEditorOptions.typeOptions || []) : []
        return [{ "value": "", "label": "All" }].concat(options)
    }
    readonly property var _roleFilterOptions: {
        const options = root.workspaceController ? (root.workspaceController.partyEditorOptions.roleOptions || []) : []
        return [{ "value": "", "label": "All" }].concat(options)
    }

    property string selectedRowId: ""
    property bool detailOpen: false
    property var _pendingConfirm: null

    // -- Inspector "Actions ▾" menu: Party's own 2-state lifecycle (Active/
    // Inactive only -- no Archive; see activate_party/deactivate_party, a
    // distinct command pair, not the generic profile update). Deactivate is
    // confirmed; Activate executes directly -- the same asymmetric
    // convention Employee/Department/Site already use.
    readonly property var _inspectorLifecycleMenuItems: {
        const item = root._selectedItem
        if (!item) return []
        if (item.isActive) {
            return [{ "id": "deactivate", "label": "Deactivate party", "icon": "reject", "enabled": root._canWrite }]
        }
        return [{ "id": "activate", "label": "Activate party", "icon": "approve", "enabled": root._canWrite }]
    }

    function _requestDeactivateConfirm(partyId, partyName) {
        root._pendingConfirm = {
            "itemId": partyId,
            "message": "Deactivate " + String(partyName || "this party") + "?",
            "supportingText": "It will no longer be available for new operational relationships. " +
                "Existing references and historical information will remain available."
        }
        confirmDialog.open()
    }

    function _performLifecycleAction(actionId, partyId, partyName) {
        if (!root.workspaceController) return
        if (actionId === "activate") {
            root.workspaceController.activateParty(partyId)
        } else if (actionId === "deactivate") {
            root._requestDeactivateConfirm(partyId, partyName)
        }
    }

    function _onInspectorMenuAction(actionId) {
        if (!root._selectedItem) return
        root._performLifecycleAction(actionId, root.selectedRowId, root._selectedItem.title)
    }

    // RBAC: gates create/edit/lifecycle buttons -- a client-side UX
    // optimization; the backend enforces "party.manage" independently
    // regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("party.manage")
        : true

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.partyCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    function _titleCaseRole(value) {
        return String(value || "").toLowerCase().replace(/_/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase() })
    }

    // Enterprise grouped Inspector layout (Identity/Business Roles/Contact/
    // Location/Registration), matching Employee's/Department's own
    // Inspector -- real per-field data, never a synthetic "Details"/"Info"
    // row. Type and Role are never conflated: Identity carries Type, a
    // dedicated Business Roles group carries the multi-valued role set.
    readonly property var _inspectorGroups: {
        const item = root._selectedItem
        if (!item) return []
        const state = item.state || {}
        const roles = (state.roles || []).map(function(r) { return root._titleCaseRole(r) })
        const groups = [
            {
                "title": "Identity",
                "rows": [
                    { "label": "Type", "value": String(state.partyTypeLabel || "") },
                    { "label": "Legal Name", "value": String(state.legalName || "") }
                ]
            },
            {
                "title": "Business Roles",
                "rows": roles.length > 0
                    ? roles.map(function(r) { return { "label": "Role", "value": r } })
                    : [{ "label": "Roles", "value": "No business roles assigned." }]
            },
            {
                "title": "Contact",
                "rows": [
                    { "label": "Email", "value": String(state.email || "") },
                    { "label": "Phone", "value": String(state.phone || "") },
                    { "label": "Website", "value": String(state.website || "") }
                ]
            },
            {
                "title": "Location",
                "rows": [
                    { "label": "City", "value": String(state.city || "") },
                    { "label": "Country", "value": String(state.country || "") }
                ]
            }
        ]
        if (String(state.registrationNumber || "").length > 0 || String(state.taxIdentifier || "").length > 0) {
            groups.push({
                "title": "Registration",
                "rows": [
                    { "label": "Registration Number", "value": String(state.registrationNumber || "") },
                    { "label": "Tax Identifier", "value": String(state.taxIdentifier || "") }
                ]
            })
        }
        return groups
    }

    function _itemById(itemId) {
        const items = root.partyCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openPartyEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    function handleDetailAction(actionId) {
        const id = root.selectedRowId
        const item = root._selectedItem
        if (actionId === "refresh") { if (root.workspaceController) root.workspaceController.refresh(); return }
        if (actionId === "edit") { root.openEdit(id); return }
        if (actionId === "activate" || actionId === "deactivate") {
            root._performLifecycleAction(actionId, id, item ? item.title : "")
            return
        }
    }

    title: "Parties"
    subtitle: String(root.partyCatalog.subtitle || "")
    showHeader: !root.detailOpen

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0
            visible: !root.detailOpen

            PlatformComponents.AdminEntityWorkspace {
                id: _adminWorkspace
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Parties"
                entityLabel: "Party"
                catalog: root.partyCatalog
                catalogModel: root.workspaceController ? root.workspaceController.partiesTableModel : null
                tableId: root._tableId
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId
                showSearch: true
                searchText: root.workspaceController ? root.workspaceController.partySearchText : ""
                pageSizeOptions: root.workspaceController ? root.workspaceController.partyPageSizeOptions : [25, 50, 100]

                AppControls.ComboBox {
                    Layout.preferredWidth: 140
                    model: root._statusFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.partyStatusFilter : ""
                        for (let i = 0; i < root._statusFilterOptions.length; i += 1) {
                            if (root._statusFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setPartyStatusFilter(String(currentValue || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 150
                    model: root._typeFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.partyTypeFilter : ""
                        for (let i = 0; i < root._typeFilterOptions.length; i += 1) {
                            if (root._typeFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setPartyTypeFilter(String(currentValue || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 160
                    model: root._roleFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.partyRoleFilter : ""
                        for (let i = 0; i < root._roleFilterOptions.length; i += 1) {
                            if (root._roleFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setPartyRoleFilter(String(currentValue || ""))
                    }
                }

                onCreateRequested: dialogHostLoader.invoke("openPartyCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onSearchChanged: function(text) {
                    if (root.workspaceController) root.workspaceController.setPartySearchText(text)
                }
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setPartyPage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController) root.workspaceController.setPartyPageSize(pageSize)
                }
                onClearFiltersRequested: {
                    if (!root.workspaceController) return
                    root.workspaceController.setPartySearchText("")
                    root.workspaceController.setPartyStatusFilter("")
                    root.workspaceController.setPartyTypeFilter("")
                    root.workspaceController.setPartyRoleFilter("")
                }
                onColumnsStateChanged: function(cols) { root._saveColumnState(cols) }
                onRefreshRequested: { if (root.workspaceController) { root.workspaceController.clearMessages(); root.workspaceController.refresh() } }
            }

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                visible: root.selectedRowId.length > 0 && Window.width >= Theme.AppTheme.compactContentBreakpoint
                panelWidth: 380
                title: root._selectedItem ? String(root._selectedItem.title || "") : ""
                statusLabel: (root._selectedItem && root._selectedItem.statusLabel)
                    ? String(root._selectedItem.statusLabel.label || "")
                    : ""
                statusTone: (root._selectedItem && root._selectedItem.statusLabel)
                    ? String(root._selectedItem.statusLabel.tone || "")
                    : ""
                groups: root._inspectorGroups
                busy: root.busy
                viewDetailsPrimary: true
                viewDetailsLabel: "Open Details"
                showViewDetailsAction: true
                editActionLabel: "Edit"
                showEditAction: root._canWrite
                menuActions: root._canWrite ? root._inspectorLifecycleMenuItems : []
                menuTriggerLabel: "Actions"

                onCloseRequested: root.selectedRowId = ""
                onEditRequested: root.openEdit(root.selectedRowId)
                onMenuActionTriggered: function(id) { root._onInspectorMenuAction(id) }
                onViewDetailsRequested: root.detailOpen = true
            }
        }

        Loader {
            anchors.fill: parent
            active: root.detailOpen
            visible: active
            asynchronous: true

            sourceComponent: Component {
                AdminPartyDetailPage {
                    platformCatalog: root.platformCatalog
                    party: root._selectedItem || ({})
                    breadcrumb: (root.breadcrumb || []).concat(
                        root._selectedItem ? [String(root._selectedItem.title || "")] : []
                    )
                    canWrite: root._canWrite
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
                platformCatalog: root.platformCatalog
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: confirmDialog
        title: "Confirm"
        confirmLabel: "Deactivate party"
        confirmIcon: "reject"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            root.workspaceController.deactivateParty(pending.itemId)
            root._pendingConfirm = null
        }
    }
}
