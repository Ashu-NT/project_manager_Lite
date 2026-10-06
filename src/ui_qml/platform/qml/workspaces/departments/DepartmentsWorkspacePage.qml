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
import Shell.Context 1.0 as ShellContexts
import "sections/DepartmentsColumnConfig.js" as ColumnConfig
import "sections/DepartmentEmployeesColumns.js" as EmployeeColumns

// Departments as a standalone Platform destination. Same shape as
// SitesWorkspacePage: server-side pagination/search/status filter/Columns,
// plus a Site filter (Department is Site-optional, unlike Site itself), the
// existing related-employees list (relatedRowActivated) and calendar-
// assignment context, reused verbatim from the facade's existing wiring,
// fixed to entityType "department".
AppLayouts.WorkspaceFrame {
    id: root
    objectName: "departmentsWorkspacePage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null
    // Threaded straight down to AdminDepartmentDetailPage's Related Actions
    // "Open Project Management" entry, which uses it to switch the
    // top-level module via the shell's own selectRoute() -- the same
    // cross-module navigation abstraction PM's own dashboard cards already
    // use in the opposite direction. Never imported by Platform business
    // logic; just a plain passed-through reference.
    property ShellContexts.ShellContext shellModel

    signal navigateToDestination(string destinationId)
    signal relatedRecordRequested(string destinationId, string rowId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var departmentCatalog: root.workspaceController
        ? root.workspaceController.departments
        : ({ "title": "Departments", "subtitle": "", "emptyState": "", "items": [] })

    readonly property string _tableId: "platform.departments.table"
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

    // "Archived" does not exist for Department -- its lifecycle is a plain
    // 2-state Active/Inactive boolean (is_active), never a 3-state enum like
    // Organization/Site.
    readonly property var _statusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]

    // Department is Site-optional (unlike Site's own workspace, which has no
    // analogous self-filter) -- built from the same active-Site options
    // already fetched for the Create/Edit dialog's Site dropdown, not a
    // separate backend call.
    readonly property var _siteFilterOptions: {
        const options = root.workspaceController ? (root.workspaceController.departmentEditorOptions.siteOptions || []) : []
        return [{ "value": "", "label": "All Sites" }].concat(options)
    }

    readonly property var _employeeColumns: EmployeeColumns.columns()

    property string selectedRowId: ""
    property bool detailOpen: false
    property var _pendingConfirm: null

    // -- Inspector "Actions ▾" menu: Department's own 2-state lifecycle
    // (Active/Inactive only -- no Archive; see activate_department/
    // deactivate_department, a distinct, guarded command pair, not the
    // generic profile update). Deactivate is confirmed (a state change with
    // real operational consequence); Activate executes directly, matching
    // the existing asymmetric convention already used for Site.
    readonly property var _inspectorLifecycleMenuItems: {
        const item = root._selectedItem
        if (!item) return []
        if (item.isActive) {
            return [{ "id": "deactivate", "label": "Deactivate department", "icon": "reject", "enabled": root._canWrite }]
        }
        return [{ "id": "activate", "label": "Activate department", "icon": "approve", "enabled": root._canWrite }]
    }

    function _requestDeactivateConfirm(departmentId, departmentName) {
        root._pendingConfirm = {
            "itemId": departmentId,
            "message": "Deactivate " + String(departmentName || "this department") + "?",
            "supportingText": "It will no longer be available for new operational activity. " +
                "Existing records and historical information will remain available."
        }
        confirmDialog.open()
    }

    function _performLifecycleAction(actionId, departmentId, departmentName) {
        if (!root.workspaceController) return
        if (actionId === "activate") {
            root.workspaceController.activateDepartment(departmentId)
        } else if (actionId === "deactivate") {
            root._requestDeactivateConfirm(departmentId, departmentName)
        }
    }

    function _onInspectorMenuAction(actionId) {
        if (!root._selectedItem) return
        root._performLifecycleAction(actionId, root.selectedRowId, root._selectedItem.title)
    }

    // RBAC: gates create/edit/set-active buttons for the department's own
    // mutations, plus the related-record "New Employee" and calendar
    // assignment actions surfaced from the department detail page -- a
    // client-side UX optimization; the backend enforces these permissions
    // independently regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("settings.manage")
        : true
    readonly property bool _canManageEmployees: root.platformCatalog
        ? root.platformCatalog.hasPermission("employee.manage")
        : true
    // Dual authorization: Calendar is a Platform capability (calendar.manage)
    // assigned to a Department target (department.manage) 
    readonly property bool _canManageCalendar: root.platformCatalog
        ? (root.platformCatalog.hasPermission("calendar.manage") && root.platformCatalog.hasPermission("department.manage"))
        : true

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.departmentCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    // Enterprise grouped Inspector layout (Identity/Structure/Key
    // Statistics/Financial Context), matching AdminOrganizationDetailPage's
    // and SitesWorkspacePage's own Inspector -- real per-field data, never a
    // synthetic "Details"/"Info" row collapsing an already-concatenated
    // subtitle/metaText string. Each group hides itself entirely when every
    // one of its rows is empty.
    readonly property var _inspectorGroups: {
        const item = root._selectedItem
        if (!item) return []
        const state = item.state || {}
        return [
            {
                "title": "Identity",
                "rows": [
                    { "label": "Type", "value": String(state.departmentType || "") },
                    { "label": "Organization", "value": String(state.organizationName || "") },
                    { "label": "Site", "value": String(state.siteName || "") }
                ]
            },
            {
                "title": "Structure",
                "rows": [
                    { "label": "Head of Department", "value": String(state.headOfDepartmentDisplay || "") },
                    { "label": "Parent Department", "value": String(state.parentDepartmentName || "") }
                ]
            },
            {
                "title": "Key Statistics",
                "rows": [
                    { "label": "Employees", "value": String(root._employeeCountFor(state) ?? "") }
                ]
            },
            {
                "title": "Financial Context",
                "rows": [
                    { "label": "Cost Center Code", "value": String(state.costCenterCode || "") }
                ]
            }
        ]
    }

    // Cheap, on-demand count for the currently inspected department only
    // (one department_id-scoped query, via the same backend Department
    // Detail's own Employees tab already uses) -- never a full-catalog N+1.
    function _employeeCountFor(state) {
        const departmentId = String(state.departmentId || state.id || "")
        if (departmentId.length === 0 || !root.workspaceController) return undefined
        const result = root.workspaceController.employeesForDepartment(departmentId)
        return result && result.items ? result.items.length : 0
    }

    readonly property var _calendarContext: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "assignedCalendar": {}, "sourceChain": [] })
        const state = item.state || {}
        const entityId = String(state.departmentId || state.id || item.id || "")
        if (!entityId.length) return ({ "assignedCalendar": {}, "sourceChain": [] })
        return root.workspaceController.calendarAssignmentContext(
            "department", entityId, String(state.siteId || ""), String(state.departmentId || "")
        )
    }
    readonly property var _calendarSummary: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "hasCalendar": false })
        const state = item.state || {}
        const departmentId = String(state.departmentId || state.id || item.id || "")
        const orgId = String(state.organizationId || "")
        if (!departmentId.length) return ({ "hasCalendar": false })
        return root.workspaceController.departmentCalendarSummary(departmentId, orgId, String(state.siteId || ""))
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
        const items = root.departmentCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openDepartmentEdit", item.state || {})
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
            const entityId = String(state.departmentId || state.id || (item ? item.id : "") || "")
            if (entityId.length) {
                dialogHostLoader.invoke("openCalendarAssign", "department", entityId, String(item.title || entityId), root._calendarOptions())
            }
            return
        }
        if (actionId === "clear_calendar_assignment") {
            const assigned = root._calendarContext.assignedCalendar || {}
            const assignmentId = String(assigned.assignmentId || "")
            if (root.workspaceController && assignmentId.length) root.workspaceController.removeCalendarAssignment(assignmentId, "department")
            return
        }
        if (actionId === "open_calendar_mgmt") {
            // Opens THIS department's actual assigned calendar row when one
            // exists (same relatedRecordRequested("calendars", calendarId)
            // cross-navigation Site Overview's "Manage Calendar" already
            // uses) -- falls back to the unfiltered Calendars workspace
            // only when this department has no override and inherits.
            const assigned = root._calendarContext.assignedCalendar || {}
            const calendarId = String(assigned.calendarId || "")
            if (calendarId.length) {
                root.relatedRecordRequested("calendars", calendarId)
            } else {
                root.navigateToDestination("calendars")
            }
            return
        }
        if (actionId === "create_employee") { dialogHostLoader.invoke("openEmployeeCreate"); return }
        if (actionId === "open_documents") { root.navigateToDestination("documents"); return }
        if (actionId === "open_project_management") {
            // "project_management" is a separate top-level module, not a
            // Platform-internal destination -- switch modules the same way
            // Site's own Related Actions do.
            if (root.shellModel) root.shellModel.selectRoute("project_management.workspace")
            return
        }
        if (actionId === "refresh") { if (root.workspaceController) root.workspaceController.refresh(); return }
        if (actionId === "edit") { root.openEdit(id); return }
        if (actionId === "activate" || actionId === "deactivate") {
            root._performLifecycleAction(actionId, id, item ? item.title : "")
            return
        }
    }

    title: "Departments"
    subtitle: String(root.departmentCatalog.subtitle || "")
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
                sectionTitle: "Departments"
                entityLabel: "Department"
                catalog: root.departmentCatalog
                catalogModel: root.workspaceController ? root.workspaceController.departmentsTableModel : null
                tableId: root._tableId
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId
                showSearch: true
                searchText: root.workspaceController ? root.workspaceController.departmentSearchText : ""
                pageSizeOptions: root.workspaceController ? root.workspaceController.departmentPageSizeOptions : [25, 50, 100]

                AppControls.ComboBox {
                    Layout.preferredWidth: 160
                    model: root._statusFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.departmentStatusFilter : ""
                        for (let i = 0; i < root._statusFilterOptions.length; i += 1) {
                            if (root._statusFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setDepartmentStatusFilter(String(currentValue || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 180
                    model: root._siteFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.departmentSiteFilter : ""
                        for (let i = 0; i < root._siteFilterOptions.length; i += 1) {
                            if (root._siteFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setDepartmentSiteFilter(String(currentValue || ""))
                    }
                }

                onCreateRequested: dialogHostLoader.invoke("openDepartmentCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onSearchChanged: function(text) {
                    if (root.workspaceController) root.workspaceController.setDepartmentSearchText(text)
                }
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setDepartmentPage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController) root.workspaceController.setDepartmentPageSize(pageSize)
                }
                onClearFiltersRequested: {
                    if (!root.workspaceController) return
                    root.workspaceController.setDepartmentSearchText("")
                    root.workspaceController.setDepartmentStatusFilter("")
                    root.workspaceController.setDepartmentSiteFilter("")
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
                AdminDepartmentDetailPage {
                    platformCatalog: root.platformCatalog
                    department: root._selectedItem || ({})
                    breadcrumb: (root.breadcrumb || []).concat(
                        root._selectedItem ? [String(root._selectedItem.title || "")] : []
                    )
                    shellModel: root.shellModel
                    canWrite: root._canWrite
                    canManageEmployees: root._canManageEmployees
                    canManageCalendar: root._canManageCalendar
                    employeeColumns: root._employeeColumns
                    deptCalendarAssignment: root._calendarContext.assignedCalendar || ({})
                    calendarSourceChain: root._calendarContext.sourceChain || []
                    deptCalendarSummary: root._calendarSummary
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
        id: confirmDialog
        title: "Confirm"
        confirmLabel: "Deactivate department"
        confirmIcon: "reject"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            root.workspaceController.deactivateDepartment(pending.itemId)
            root._pendingConfirm = null
        }
    }
}
