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
import "sections/SitesColumnConfig.js" as ColumnConfig
import "sections/SiteDepartmentsColumns.js" as DepartmentColumns
import "sections/SiteEmployeesColumns.js" as EmployeeColumns

// R4: Sites as a standalone Platform destination. Same shape as
// OrganizationsWorkspacePage, plus: the existing AdminSiteDetailPage's
// related-departments list (relatedRowActivated) and calendar-assignment
// context, both reused verbatim from the facade's existing wiring.
AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    // Bubbled to PlatformWorkspacePage: plain destination switch (no target
    // row), e.g. a "manage departments" toolbar action.
    signal navigateToDestination(string destinationId)
    // Bubbled to PlatformWorkspacePage: switch destination AND open a
    // specific related record there (e.g. clicking a department shown
    // inside a site's detail page).
    signal relatedRecordRequested(string destinationId, string rowId)

    // Called by PlatformWorkspacePage when another page's related-record
    // link points here.
    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var siteCatalog: root.workspaceController
        ? root.workspaceController.sites
        : ({ "title": "Sites", "subtitle": "", "emptyState": "", "items": [] })
    property var employeeCatalog: root.workspaceController
        ? root.workspaceController.employees
        : ({ "title": "Employees", "subtitle": "", "emptyState": "", "items": [] })

    readonly property string _tableId: "platform.sites.table"
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

    readonly property var _departmentColumns: DepartmentColumns.columns()
    readonly property var _employeeColumns: EmployeeColumns.columns()
    // "Archived" is deliberately not offered here -- the backend list_sites_
    // page_for_organization filter is still the legacy active_only boolean
    // (active vs. "not active"), which cannot distinguish inactive from
    // archived. Add it once that filter is upgraded to a real status string
    // (matching Organization's own list filter), not before.
    readonly property var _statusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]

    property string selectedRowId: ""
    property bool detailOpen: false

    // RBAC: gates create/edit/enable buttons -- a client-side UX
    // optimization; the backend enforces these permissions independently
    // regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("settings.manage")
        : true
    readonly property bool _canManageEmployees: root.platformCatalog
        ? root.platformCatalog.hasPermission("employee.manage")
        : true
    readonly property bool _canManageCalendar: root.platformCatalog
        ? root.platformCatalog.hasPermission("task.manage")
        : true

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.siteCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    // Enterprise grouped Inspector layout (Identity/Lifecycle/Location/
    // Business Context), matching AdminOrganizationDetailPage's own
    // Inspector -- real per-field data, never a synthetic "Details"/"Info"
    // row collapsing an already-concatenated subtitle/metaText string. Each
    // group hides itself entirely when every one of its rows is empty.
    readonly property var _inspectorGroups: {
        const item = root._selectedItem
        if (!item) return []
        const state = item.state || {}
        return [
            {
                "title": "Identity",
                "rows": [
                    { "label": "Code", "value": String(state.siteCode || "") },
                    { "label": "Site Type", "value": String(state.siteType || "") },
                    { "label": "Organization", "value": String(state.organizationName || "") }
                ]
            },
            {
                "title": "Lifecycle",
                "rows": [
                    { "label": "Status", "value": item.statusLabel ? String(item.statusLabel.label || "") : "" }
                ]
            },
            {
                "title": "Location",
                "rows": [
                    { "label": "City", "value": String(state.city || "") },
                    { "label": "Country", "value": String(state.country || "") },
                    { "label": "Timezone", "value": String(state.timezoneName || "") }
                ]
            },
            {
                "title": "Key Statistics",
                "rows": [
                    { "label": "Departments", "value": String(root._departmentCountFor(state) ?? "") },
                    { "label": "Employees", "value": String(root._employeeCountFor(state) ?? "") }
                ]
            },
            {
                "title": "Business Context",
                "rows": [
                    { "label": "Currency", "value": String(state.currencyCode || "") },
                    { "label": "Notes", "value": String(state.notes || "") }
                ]
            }
        ]
    }

    // Cheap, on-demand counts for the currently inspected site only (one
    // site_id-scoped query each, via the same backend Site Detail's own
    // Departments/Employees tabs already use) -- never a full-catalog N+1.
    function _departmentCountFor(state) {
        const siteId = String(state.siteId || state.id || "")
        if (siteId.length === 0 || !root.workspaceController) return undefined
        const result = root.workspaceController.departmentsForSite(siteId)
        return result && result.items ? result.items.length : 0
    }
    function _employeeCountFor(state) {
        const siteId = String(state.siteId || state.id || "")
        if (siteId.length === 0 || !root.workspaceController) return undefined
        const result = root.workspaceController.employeesForSite(siteId)
        return result && result.items ? result.items.length : 0
    }

    // -- Inspector "Actions ▾" menu: full 3-state lifecycle (Active/
    // Inactive/Archived), matching AdminOrganizationDetailPage's own menu
    // exactly. Archived is terminal (see SiteService -- the same guarded
    // 3-state model as Organization) -- the menu is simply empty then.
    readonly property var _inspectorLifecycleMenuItems: {
        const item = root._selectedItem
        if (!item) return []
        const status = item.state ? String(item.state.status || "") : ""
        const items = []
        if (status === "active") {
            items.push({ "id": "deactivate", "label": "Deactivate site", "icon": "reject", "enabled": root._canWrite })
            items.push({ "id": "archive", "label": "Archive site", "icon": "inventory", "danger": true, "enabled": root._canWrite })
        } else if (status === "inactive") {
            items.push({ "id": "activate", "label": "Activate site", "icon": "approve", "enabled": root._canWrite })
            items.push({ "id": "archive", "label": "Archive site", "icon": "inventory", "danger": true, "enabled": root._canWrite })
        }
        return items
    }

    property var _pendingConfirm: null

    function _requestLifecycleConfirm(action, siteId, siteName) {
        const name = siteName || "this site"
        if (action === "deactivate") {
            root._pendingConfirm = {
                "action": "deactivate", "siteId": siteId,
                "message": "Deactivate " + name + "?",
                "supportingText": name + " will no longer be available for new operational activity. " +
                    "Existing records and historical information will remain available."
            }
        } else if (action === "archive") {
            root._pendingConfirm = {
                "action": "archive", "siteId": siteId,
                "message": "Archive " + name + "?",
                "supportingText": name + " will be retired from normal operational use and retained for " +
                    "historical reference. This action cannot be reversed through the normal Site workspace."
            }
        } else {
            return
        }
        _lifecycleConfirmDialog.open()
    }

    // Shared by the Inspector's own Actions ▾ menu and the Detail header's
    // Actions ▾ menu (bubbled up via handleDetailAction below) -- one
    // dialog instance, not duplicated per surface.
    function _performLifecycleAction(actionId, siteId, siteName) {
        if (!root.workspaceController) return
        if (actionId === "activate") {
            root.workspaceController.activateSite(siteId)
        } else if (actionId === "deactivate" || actionId === "archive") {
            root._requestLifecycleConfirm(actionId, siteId, siteName)
        }
    }

    function _onInspectorMenuAction(actionId) {
        if (!root._selectedItem) return
        root._performLifecycleAction(actionId, root.selectedRowId, root._selectedItem.title)
    }

    // Calendar assignment context for the selected site -- same formula as
    // AdminConsolePage.qml's _calendarAssignmentContext/_calendarEntityId,
    // fixed to entityType "site" since this page only ever handles sites.
    readonly property var _calendarContext: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "assignedCalendar": {}, "sourceChain": [] })
        const state = item.state || {}
        const entityId = String(state.siteId || state.id || item.id || "")
        if (!entityId.length) return ({ "assignedCalendar": {}, "sourceChain": [] })
        return root.workspaceController.calendarAssignmentContext(
            "site", entityId, String(state.siteId || ""), String(state.departmentId || "")
        )
    }
    readonly property var _calendarSummary: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "hasCalendar": false })
        const state = item.state || {}
        const siteId = String(state.siteId || state.id || item.id || "")
        const orgId = String(state.organizationId || "")
        if (!siteId.length) return ({ "hasCalendar": false })
        return root.workspaceController.siteCalendarSummary(siteId, orgId)
    }

    function _calendarOptions() {
        const rows = root.workspaceController ? (root.workspaceController.calendars.items || []) : []
        const options = []
        for (let i = 0; i < rows.length; i += 1) {
            const item = rows[i] || {}
            const state = item.state || {}
            const id = String(state.calendarId || state.id || item.id || "")
            if (!id.length) continue
            options.push({
                "id": id,
                "name": String(state.name || item.title || id),
                "code": String(state.code || ""),
                "calendarType": String(state.calendarType || item.statusLabel || "")
            })
        }
        return options
    }

    function _itemById(itemId) {
        const items = root.siteCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openSiteEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    function handleDetailAction(actionId) {
        const id = root.selectedRowId
        const item = root._selectedItem
        if (actionId === "assign_calendar") {
            const state = item ? (item.state || {}) : {}
            const entityId = String(state.siteId || state.id || (item ? item.id : "") || "")
            if (entityId.length) {
                dialogHostLoader.invoke("openCalendarAssign", "site", entityId, String(item.title || entityId), root._calendarOptions())
            }
            return
        }
        if (actionId === "clear_calendar_assignment") {
            const assigned = root._calendarContext.assignedCalendar || {}
            const assignmentId = String(assigned.assignmentId || "")
            if (root.workspaceController && assignmentId.length) root.workspaceController.removeCalendarAssignment(assignmentId, "site")
            return
        }
        if (actionId === "open_calendar_mgmt") {
            // Opens THIS site's actual assigned calendar row when one exists
            // (same relatedRecordRequested("calendars", calendarId) cross-
            // navigation Organization Overview's "Manage Calendar" already
            // uses) -- falls back to the unfiltered Calendars workspace only
            // when this site has no override (inherits the Organization
            // default), since there is no specific calendar row to open then.
            const assigned = root._calendarContext.assignedCalendar || {}
            const calendarId = String(assigned.calendarId || "")
            if (calendarId.length) {
                root.relatedRecordRequested("calendars", calendarId)
            } else {
                root.navigateToDestination("calendars")
            }
            return
        }
        if (actionId === "create_department") { dialogHostLoader.invoke("openDepartmentCreate"); return }
        if (actionId === "create_employee") { dialogHostLoader.invoke("openEmployeeCreate"); return }
        if (actionId === "refresh") { if (root.workspaceController) root.workspaceController.refresh(); return }
        if (actionId === "edit") { root.openEdit(id); return }
        if (actionId === "activate" || actionId === "deactivate" || actionId === "archive") {
            root._performLifecycleAction(actionId, id, item ? item.title : "")
            return
        }
    }

    title: "Sites"
    subtitle: String(root.siteCatalog.subtitle || "")
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
                sectionTitle: "Sites"
                entityLabel: "Site"
                catalog: root.siteCatalog
                catalogModel: root.workspaceController ? root.workspaceController.sitesTableModel : null
                tableId: root._tableId
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId
                showSearch: true
                searchText: root.workspaceController ? root.workspaceController.siteSearchText : ""
                pageSizeOptions: root.workspaceController ? root.workspaceController.sitePageSizeOptions : [25, 50, 100]

                AppControls.ComboBox {
                    Layout.preferredWidth: 160
                    model: root._statusFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.siteStatusFilter : ""
                        for (let i = 0; i < root._statusFilterOptions.length; i += 1) {
                            if (root._statusFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setSiteStatusFilter(String(currentValue || ""))
                    }
                }

                onCreateRequested: dialogHostLoader.invoke("openSiteCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onSearchChanged: function(text) {
                    if (root.workspaceController) root.workspaceController.setSiteSearchText(text)
                }
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setSitePage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController) root.workspaceController.setSitePageSize(pageSize)
                }
                onClearFiltersRequested: {
                    if (!root.workspaceController) return
                    root.workspaceController.setSiteSearchText("")
                    root.workspaceController.setSiteStatusFilter("")
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
                // Enterprise action hierarchy: "Open Details" is the primary,
                // full-width action; "Edit" and the lifecycle "Actions ▾"
                // menu share the secondary row beneath it.
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
                AdminSiteDetailPage {
                    platformCatalog: root.platformCatalog
                    site: root._selectedItem || ({})
                    breadcrumb: (root.breadcrumb || []).concat(
                        root._selectedItem ? [String(root._selectedItem.title || "")] : []
                    )
                    canWrite: root._canWrite
                    canManageEmployees: root._canManageEmployees
                    canManageCalendar: root._canManageCalendar
                    departmentColumns: root._departmentColumns
                    employeeCatalog: root.employeeCatalog
                    employeeColumns: root._employeeColumns
                    siteCalendarAssignment: root._calendarContext.assignedCalendar || ({})
                    calendarSourceChain: root._calendarContext.sourceChain || []
                    siteCalendarSummary: root._calendarSummary
                    busy: root.busy
                    errorMessage: root.err
                    feedbackMessage: root.ok

                    onBackRequested: root.closeDetail()
                    onActionRequested: function(actionId) { root.handleDetailAction(actionId) }
                    onRelatedRowActivated: function(sectionId, rowId) {
                        root.relatedRecordRequested(sectionId, rowId)
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

    AppControls.ConfirmationDialog {
        id: _lifecycleConfirmDialog
        title: "Confirm"
        confirmLabel: root._pendingConfirm && root._pendingConfirm.action === "archive" ? "Archive site" : "Deactivate site"
        confirmIcon: root._pendingConfirm && root._pendingConfirm.action === "archive" ? "inventory" : "reject"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            if (pending.action === "deactivate") root.workspaceController.deactivateSite(pending.siteId)
            else if (pending.action === "archive") root.workspaceController.archiveSite(pending.siteId)
            root._pendingConfirm = null
        }
    }
}
