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
import "OrganizationsColumnConfig.js" as ColumnConfig


AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    // Bubbled up to PlatformWorkspacePage so this page can jump to another
    // Platform destination (e.g. the merged Control -> Audit) without
    // depending on the Admin Console facade's own internal sections.
    signal navigateToDestination(string destinationId)

    property var organizationCatalog: root.workspaceController
        ? root.workspaceController.organizations
        : ({ "title": "Organizations", "subtitle": "", "emptyState": "", "items": [] })

    readonly property string _tableId: "platform.organizations.table"
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

    property string selectedRowId: ""
    property bool detailOpen: false

    // RBAC: gates create/edit/enable buttons -- a client-side UX
    // optimization; a
    // the backend enforces "settings.manage" independently regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("settings.manage")
        : true

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.organizationCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    // Real per-organization aggregate counts (one aggregate query each, via
    // the same backend Organization Detail's Overview uses) -- fetched once
    // per selection, not per row, so this stays cheap regardless of how
    // many rows the table has.
    property var _detailContext: ({ "statistics": ({}) })
    function _reloadDetailContext() {
        if (!root.workspaceController || root.selectedRowId.length === 0) {
            root._detailContext = ({ "statistics": ({}) })
            return
        }
        root._detailContext = root.workspaceController.organizationDetailContext(root.selectedRowId)
    }
    onSelectedRowIdChanged: root._reloadDetailContext()
    readonly property var _statistics: root._detailContext.statistics || ({})

    // Rows with an empty value are hidden automatically by InspectorPanel --
    // an organization that hasn't filled in legal/address/contact fields yet
    // simply shows fewer rows, never a blank label or a placeholder.
    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }

    readonly property var _inspectorSections: {
        const item = root._selectedItem
        if (!item) return []
        const streetLine = root._joinNonEmpty([item.addressLine1, item.addressLine2], ", ")
        const localityLine = root._joinNonEmpty(
            [item.postalCode, item.city, item.stateRegion, item.countryName || item.countryCode],
            ", "
        )
        const stats = root._statistics
        return [
            // -- Always-populated identity/config fields ------------------
            { "label": "Code", "value": String(item.organizationCode || "") },
            // -- Legal identity (blank until filled in) --------------------
            { "label": "Legal Name", "value": String(item.legalName || "") },
            { "label": "Registration Number", "value": String(item.registrationNumber || "") },
            { "label": "Tax / VAT ID", "value": String(item.taxId || "") },
            { "label": "Timezone", "value": String(item.timezoneName || "") },
            { "label": "Base Currency", "value": String(item.baseCurrency || "") },
            // -- Real aggregate counts (one query each; never hidden --
            // "0" is real information, not a blank field) ------------------
            { "label": "Sites", "value": stats.siteCount !== undefined ? String(stats.siteCount) : "" },
            { "label": "Departments", "value": stats.departmentCount !== undefined ? String(stats.departmentCount) : "" },
            { "label": "Employees", "value": stats.employeeCount !== undefined ? String(stats.employeeCount) : "" },
            { "label": "Documents", "value": stats.documentCount !== undefined ? String(stats.documentCount) : "" },
            // -- Registered address (blank until filled in) ----------------
            { "label": "Address", "value": streetLine },
            { "label": "City / Postal / Country", "value": localityLine },
            // -- Contact (blank until filled in) ---------------------------
            { "label": "Email", "value": String(item.email || "") },
            { "label": "Phone", "value": String(item.phone || "") },
            { "label": "Website", "value": String(item.website || "") }
        ]
    }

    function _itemById(itemId) {
        const items = root.organizationCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function _clearMessages() {
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    // -- Bulk actions (row-selection checkboxes + BulkActionBar) ------------
    readonly property var _editorOptions: root.workspaceController
        ? root.workspaceController.organizationEditorOptions
        : ({})
    readonly property var _bulkChangeProperties: [
        {
            "id": "status", "label": "Status",
            "values": [{ "value": "enabled", "label": "Enabled" }, { "value": "disabled", "label": "Disabled" }]
        },
        { "id": "currency", "label": "Base Currency", "values": root._editorOptions.currencyOptions || [] },
        { "id": "timezone", "label": "Timezone", "values": root._editorOptions.timezoneOptions || [] }
    ]
    readonly property var _bulkModuleOptions: root._editorOptions.moduleOptions || []
    readonly property int _selectedCount: root.workspaceController
        ? (root.workspaceController.selectedOrganizationIds || []).length
        : 0

    function _applyBulkProperty(payload) {
        if (!root.workspaceController) return
        if (payload.propertyId === "status") {
            root.workspaceController.applyBulkOrganizationStatus(payload)
        } else if (payload.propertyId === "currency") {
            root.workspaceController.applyBulkOrganizationCurrency(payload)
        } else if (payload.propertyId === "timezone") {
            root.workspaceController.applyBulkOrganizationTimezone(payload)
        }
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openOrganizationEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        root._clearMessages()
    }

    title: "Organizations"
    subtitle: String(root.organizationCatalog.subtitle || "")
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
                sectionTitle: "Organizations"
                entityLabel: "Organization"
                catalog: root.organizationCatalog
                catalogModel: root.workspaceController ? root.workspaceController.organizationsTableModel : null
                tableId: root._tableId
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId
                showSearch: true
                searchText: root.workspaceController ? root.workspaceController.organizationSearchText : ""
                pageSizeOptions: root.workspaceController ? root.workspaceController.organizationPageSizeOptions : [25, 50, 100]
                multiSelect: root._canWrite
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedOrganizationIds || []) : []
                bulkActions: [
                    { "id": "change_property", "label": "Change Property", "icon": "edit", "danger": false, "enabled": true },
                    { "id": "assign_modules", "label": "Assign Modules", "icon": "module", "danger": false, "enabled": true }
                ]

                onCreateRequested: dialogHostLoader.invoke("openOrganizationCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
                onSearchChanged: function(text) {
                    if (root.workspaceController) root.workspaceController.setOrganizationSearchText(text)
                }
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setOrganizationPage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController) root.workspaceController.setOrganizationPageSize(pageSize)
                }
                onClearFiltersRequested: {
                    if (root.workspaceController) root.workspaceController.setOrganizationSearchText("")
                }
                onColumnsStateChanged: function(cols) { root._saveColumnState(cols) }
                onRowSelectionToggled: function(id, selected) {
                    if (root.workspaceController) root.workspaceController.setOrganizationBulkSelection(id, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    if (!root.workspaceController) return
                    if (allSelected) root.workspaceController.selectVisibleOrganizations()
                    else root.workspaceController.clearOrganizationBulkSelection()
                }
                onBulkCancelRequested: {
                    if (root.workspaceController) root.workspaceController.clearOrganizationBulkSelection()
                }
                onBulkActionRequested: function(actionId) {
                    if (actionId === "change_property") {
                        _bulkChangePopup.anchorItem = _adminWorkspace.bulkActionBar.actionButtonForId("change_property")
                        _bulkChangePopup.open()
                    } else if (actionId === "assign_modules") {
                        _bulkModulePopup.anchorItem = _adminWorkspace.bulkActionBar.actionButtonForId("assign_modules")
                        _bulkModulePopup.open()
                    }
                }
            }

            AppWidgets.BulkChangePropertyPopup {
                id: _bulkChangePopup
                title: "Bulk Update Organizations"
                selectedCount: root._selectedCount
                busy: root.busy
                properties: root._bulkChangeProperties

                onApplyRequested: function(payload) { root._applyBulkProperty(payload) }
            }

            AppWidgets.BulkModuleAssignmentPopup {
                id: _bulkModulePopup
                selectedCount: root._selectedCount
                busy: root.busy
                moduleOptions: root._bulkModuleOptions

                onApplyRequested: function(payload) {
                    if (root.workspaceController) root.workspaceController.applyBulkOrganizationModules(payload)
                }
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
                secondaryActionLabel: root._selectedItem && root._selectedItem.statusLabel === "Enabled" ? "Disable" : "Enable"
                showSecondaryAction: root._canWrite
                viewDetailsLabel: "View Details"
                showViewDetailsAction: true

                onCloseRequested: root.selectedRowId = ""
                onEditRequested: root.openEdit(root.selectedRowId)
                onSecondaryActionRequested: {
                    if (!root.workspaceController) return
                    if (root._selectedItem && root._selectedItem.statusLabel === "Enabled") {
                        root.workspaceController.disableOrganization(root.selectedRowId)
                    } else {
                        root.workspaceController.enableOrganization(root.selectedRowId)
                    }
                }
                onViewDetailsRequested: root.detailOpen = true
            }
        }

        Loader {
            id: _detailLoader
            anchors.fill: parent
            active: root.detailOpen
            visible: active
            asynchronous: true

            sourceComponent: Component {
                AdminOrganizationDetailPage {
                    organization: root._selectedItem || ({})
                    workspaceController: root.workspaceController
                    platformCatalog: root.platformCatalog
                    breadcrumb: (root.breadcrumb || []).concat(
                        root._selectedItem ? [String(root._selectedItem.title || "")] : []
                    )
                    canWrite: root._canWrite
                    busy: root.busy
                    errorMessage: root.err
                    feedbackMessage: root.ok

                    onBackRequested: root.closeDetail()
                    onNavigateToDestination: function(destinationId) {
                        root.navigateToDestination(destinationId)
                    }

                    onActionRequested: function(actionId) {
                        if (actionId === "edit") {
                            root.openEdit(root.selectedRowId)
                        } else if (actionId === "enable") {
                            if (root.workspaceController)
                                root.workspaceController.enableOrganization(root.selectedRowId)
                        } else if (actionId === "disable") {
                            if (root.workspaceController)
                                root.workspaceController.disableOrganization(root.selectedRowId)
                        } else if (actionId === "refresh") {
                            if (root.workspaceController)
                                root.workspaceController.refresh()
                        } else if (actionId === "show_audit") {
                            root.navigateToDestination("control_audit")
                        }
                    }
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
}
