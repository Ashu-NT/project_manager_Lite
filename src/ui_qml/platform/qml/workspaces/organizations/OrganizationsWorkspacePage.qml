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

    // organizationCode/city/countryCode are real Organization fields, auto-
    // flattened onto each row's top level from `state` by serialize_action_item
    // (see serializers.py) -- referenced here directly, not invented.
    readonly property var _columns: [
        { key: "title",          label: "Name",    flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "organizationCode", label: "Code",  flex: 1, minWidth: 110, sortable: false, visible: true },
        { key: "statusLabel",    label: "Status",  flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "city",           label: "City",    flex: 2, minWidth: 120, sortable: false, visible: true, hideBelow: Theme.AppTheme.compactContentBreakpoint },
        { key: "countryCode",    label: "Country", flex: 1, minWidth: 90,  sortable: false, visible: true, hideBelow: Theme.AppTheme.compactContentBreakpoint }
    ]

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
            [item.postalCode, item.city, item.stateRegion, item.countryCode],
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
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Organizations"
                entityLabel: "Organization"
                catalog: root.organizationCatalog
                catalogModel: root.workspaceController ? root.workspaceController.organizationsTableModel : null
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
                secondaryActionLabel: "Enable"
                showSecondaryAction: root._canWrite
                viewDetailsLabel: "View Details"
                showViewDetailsAction: true

                onCloseRequested: root.selectedRowId = ""
                onEditRequested: root.openEdit(root.selectedRowId)
                onSecondaryActionRequested: {
                    if (root.workspaceController) root.workspaceController.enableOrganization(root.selectedRowId)
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
