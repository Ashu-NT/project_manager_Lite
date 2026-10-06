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
import "sections/EmployeesColumnConfig.js" as ColumnConfig
import workspaces.employees.dialogs 1.0 as EmployeeDialogs

// Employees as a standalone Platform destination. Same shape as
// DepartmentsWorkspacePage: server-side pagination/search/status filter/
// Columns, plus Department and Site filters, the existing calendar-
// assignment context (fixed to entityType "employee") and the newly
// hardened System Access relationship (link/unlink User account) -- reused
// verbatim from the facade's existing wiring.
AppLayouts.WorkspaceFrame {
    id: root
    objectName: "employeesWorkspacePage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null
    // Threaded straight down to AdminEmployeeDetailPage's Related Actions
    // "Open Resource in Project Management" entry, which uses it to switch
    // the top-level module via the shell's own selectRoute(). Never
    // imported by Platform business logic; just a plain passed-through
    // reference.
    property ShellContexts.ShellContext shellModel

    signal navigateToDestination(string destinationId)
    signal relatedRecordRequested(string destinationId, string rowId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var employeeCatalog: root.workspaceController
        ? root.workspaceController.employees
        : ({ "title": "Employees", "subtitle": "", "emptyState": "", "items": [] })

    readonly property string _tableId: "platform.employees.table"
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

    // Employee lifecycle is a plain 2-state Active/Inactive (see
    // EmployeeLifecycleStatus) -- never a 3-state enum like Organization.
    readonly property var _statusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]

    readonly property var _departmentFilterOptions: {
        const options = root.workspaceController ? (root.workspaceController.employeeEditorOptions.departmentOptions || []) : []
        return [{ "value": "", "label": "All Departments" }].concat(options)
    }

    readonly property var _siteFilterOptions: {
        const options = root.workspaceController ? (root.workspaceController.employeeEditorOptions.siteOptions || []) : []
        return [{ "value": "", "label": "All Sites" }].concat(options)
    }

    property string selectedRowId: ""
    property bool detailOpen: false
    property var _pendingConfirm: null

    // -- Inspector "Actions ▾" menu: Employee's own 2-state lifecycle
    // (Active/Inactive only -- no Archive; see activate_employee/
    // deactivate_employee, a distinct, guarded command pair, not the
    // generic profile update). Deactivate is confirmed (a state change with
    // real operational consequence, and may be blocked by the HOD guard);
    // Activate executes directly, matching the existing asymmetric
    // convention already used for Department/Site.
    readonly property var _inspectorLifecycleMenuItems: {
        const item = root._selectedItem
        if (!item) return []
        if (item.isActive) {
            return [{ "id": "deactivate", "label": "Deactivate employee", "icon": "reject", "enabled": root._canWrite }]
        }
        return [{ "id": "activate", "label": "Activate employee", "icon": "approve", "enabled": root._canWrite }]
    }

    function _requestDeactivateConfirm(employeeId, employeeName) {
        root._pendingConfirm = {
            "itemId": employeeId,
            "message": "Deactivate " + String(employeeName || "this employee") + "?",
            "supportingText": "They will no longer be available for new operational activity. " +
                "Existing records and historical information will remain available."
        }
        confirmDialog.open()
    }

    function _performLifecycleAction(actionId, employeeId, employeeName) {
        if (!root.workspaceController) return
        if (actionId === "activate") {
            root.workspaceController.activateEmployee(employeeId)
        } else if (actionId === "deactivate") {
            root._requestDeactivateConfirm(employeeId, employeeName)
        }
    }

    function _onInspectorMenuAction(actionId) {
        if (!root._selectedItem) return
        root._performLifecycleAction(actionId, root.selectedRowId, root._selectedItem.title)
    }

    // RBAC: gates create/edit/lifecycle/System Access buttons, plus the
    // calendar assignment actions surfaced from the detail page -- a
    // client-side UX optimization; the backend enforces these permissions
    // ("employee.manage"/"auth.manage"/"task.manage") independently
    // regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("employee.manage")
        : true
    readonly property bool _canManageSystemAccess: root.platformCatalog
        ? root.platformCatalog.hasPermission("employee.manage") && root.platformCatalog.hasPermission("auth.manage")
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
        const items = root.employeeCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    // Resolves this Employee's linked User account (identity + status) on
    // demand -- a single per-employee lookup, never a batch/N+1 resolution
    // across the whole visible page (see resolve_linked_user).
    function _systemAccessFor(state) {
        const userId = String((state && state.userId) || "")
        if (userId.length === 0 || !root.workspaceController) {
            return { "linked": false, "identity": "", "isActive": false }
        }
        const resolved = root.workspaceController.resolveLinkedUser(userId) || {}
        if (!resolved.userId) return { "linked": false, "identity": "", "isActive": false }
        return { "linked": true, "identity": String(resolved.identity || ""), "isActive": resolved.isActive === true }
    }

    // Enterprise grouped Inspector layout (Employment/Organization/Contact/
    // System Access), matching Department's/Site's own Inspector -- real
    // per-field data, never a synthetic "Details"/"Info" row. System Access
    // only appears when a User account is actually linked.
    readonly property var _inspectorGroups: {
        const item = root._selectedItem
        if (!item) return []
        const state = item.state || {}
        const groups = [
            {
                "title": "Employment",
                "rows": [
                    { "label": "Job Title", "value": String(state.jobTitle || "") },
                    { "label": "Employment Type", "value": String(state.employmentType || "").replace(/_/g, " ") }
                ]
            },
            {
                "title": "Organization",
                "rows": [
                    { "label": "Organization", "value": String(state.organizationName || "") },
                    { "label": "Department", "value": String(state.departmentName || "") },
                    { "label": "Site", "value": String(state.siteName || "") }
                ]
            },
            {
                "title": "Contact",
                "rows": [
                    { "label": "Email", "value": String(state.email || "") },
                    { "label": "Phone", "value": String(state.phone || "") }
                ]
            }
        ]
        const access = root._systemAccessFor(state)
        if (access.linked) {
            groups.push({
                "title": "System Access",
                "rows": [
                    { "label": "User Account", "value": access.identity },
                    { "label": "Account Status", "value": access.isActive ? "Active" : "Inactive" }
                ]
            })
        }
        return groups
    }

    readonly property var _calendarContext: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "assignedCalendar": {}, "sourceChain": [] })
        const state = item.state || {}
        const entityId = String(state.employeeId || state.id || "")
        if (!entityId.length) return ({ "assignedCalendar": {}, "sourceChain": [] })
        return root.workspaceController.calendarAssignmentContext(
            "employee", entityId, String(state.siteId || ""), String(state.departmentId || "")
        )
    }
    readonly property var _calendarSummary: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "hasCalendar": false })
        const state = item.state || {}
        const employeeId = String(state.employeeId || state.id || item.id || "")
        const orgId = String(state.organizationId || "")
        if (!employeeId.length) return ({ "hasCalendar": false })
        return root.workspaceController.employeeCalendarSummary(
            employeeId, orgId, String(state.departmentId || ""), String(state.siteId || "")
        )
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
        const items = root.employeeCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openEmployeeEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    function _openUserLink(employeeId, employeeLabel) {
        if (!root.workspaceController) return
        const options = root.workspaceController.linkableUserOptions(employeeId) || []
        dialogHostLoader.invoke("openEmployeeUserLink", employeeId, employeeLabel, options)
    }

    function handleDetailAction(actionId) {
        const id = root.selectedRowId
        const item = root._selectedItem
        const state = item ? (item.state || {}) : {}
        if (actionId === "assign_calendar") {
            const entityId = String(state.employeeId || state.id || (item ? item.id : "") || "")
            if (entityId.length) {
                dialogHostLoader.invoke("openCalendarAssign", "employee", entityId, String(item.title || entityId), root._calendarOptions())
            }
            return
        }
        if (actionId === "clear_calendar_assignment") {
            const assigned = root._calendarContext.assignedCalendar || {}
            const assignmentId = String(assigned.assignmentId || "")
            if (root.workspaceController && assignmentId.length) root.workspaceController.removeCalendarAssignment(assignmentId, "employee")
            return
        }
        if (actionId === "open_calendar_mgmt") {
            const assigned = root._calendarContext.assignedCalendar || {}
            const calendarId = String(assigned.calendarId || "")
            if (calendarId.length) {
                root.relatedRecordRequested("calendars", calendarId)
            } else {
                root.navigateToDestination("calendars")
            }
            return
        }
        if (actionId === "link_user_account") {
            root._openUserLink(id, item ? item.title : "")
            return
        }
        if (actionId === "unlink_user_account") {
            if (root.workspaceController) root.workspaceController.unlinkEmployeeUserAccount(id)
            return
        }
        if (actionId === "open_user_account") {
            const access = root._systemAccessFor(state)
            if (access.linked) root.relatedRecordRequested("users", String(state.userId || ""))
            return
        }
        if (actionId === "add_document") {
            dialogHostLoader.invoke("openEmployeeDocumentLink", id, item ? item.title : "")
            return
        }
        if (actionId === "open_project_management") {
            // "project_management" is a separate top-level module, not a
            // Platform-internal destination -- switch modules the same way
            // Department's/Site's own Related Actions do.
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

    title: "Employees"
    subtitle: String(root.employeeCatalog.subtitle || "")
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
                sectionTitle: "Employees"
                entityLabel: "Employee"
                catalog: root.employeeCatalog
                catalogModel: root.workspaceController ? root.workspaceController.employeesTableModel : null
                tableId: root._tableId
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId
                showSearch: true
                searchText: root.workspaceController ? root.workspaceController.employeeSearchText : ""
                pageSizeOptions: root.workspaceController ? root.workspaceController.employeePageSizeOptions : [25, 50, 100]

                AppControls.ComboBox {
                    Layout.preferredWidth: 150
                    model: root._statusFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.employeeStatusFilter : ""
                        for (let i = 0; i < root._statusFilterOptions.length; i += 1) {
                            if (root._statusFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setEmployeeStatusFilter(String(currentValue || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 190
                    model: root._departmentFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.employeeDepartmentFilter : ""
                        for (let i = 0; i < root._departmentFilterOptions.length; i += 1) {
                            if (root._departmentFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setEmployeeDepartmentFilter(String(currentValue || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 180
                    model: root._siteFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.employeeSiteFilter : ""
                        for (let i = 0; i < root._siteFilterOptions.length; i += 1) {
                            if (root._siteFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setEmployeeSiteFilter(String(currentValue || ""))
                    }
                }

                onCreateRequested: dialogHostLoader.invoke("openEmployeeCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onSearchChanged: function(text) {
                    if (root.workspaceController) root.workspaceController.setEmployeeSearchText(text)
                }
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setEmployeePage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController) root.workspaceController.setEmployeePageSize(pageSize)
                }
                onClearFiltersRequested: {
                    if (!root.workspaceController) return
                    root.workspaceController.setEmployeeSearchText("")
                    root.workspaceController.setEmployeeStatusFilter("")
                    root.workspaceController.setEmployeeDepartmentFilter("")
                    root.workspaceController.setEmployeeSiteFilter("")
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
                AdminEmployeeDetailPage {
                    platformCatalog: root.platformCatalog
                    employee: root._selectedItem || ({})
                    breadcrumb: (root.breadcrumb || []).concat(
                        root._selectedItem ? [String(root._selectedItem.title || "")] : []
                    )
                    shellModel: root.shellModel
                    canWrite: root._canWrite
                    canManageSystemAccess: root._canManageSystemAccess
                    canManageCalendar: root._canManageCalendar
                    empCalendarAssignment: root._calendarContext.assignedCalendar || ({})
                    calendarSourceChain: root._calendarContext.sourceChain || []
                    empCalendarSummary: root._calendarSummary
                    systemAccess: root._systemAccessFor((root._selectedItem || {}).state || {})
                    busy: root.busy
                    errorMessage: root.err
                    feedbackMessage: root.ok

                    onBackRequested: root.closeDetail()
                    onActionRequested: function(actionId) { root.handleDetailAction(actionId) }
                    onRelatedRowActivated: function(sectionId, rowId) {
                        if (sectionId === "documents" && root.workspaceController) {
                            // Pre-selects the Document in the shared
                            // Document controller's own state before
                            // navigating -- the same two-step sequence
                            // Organization Detail's own Documents tab
                            // already uses (see AdminOrganizationDetailPage.qml).
                            root.workspaceController.selectDocument(rowId)
                        }
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
        confirmLabel: "Deactivate employee"
        confirmIcon: "reject"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            root.workspaceController.deactivateEmployee(pending.itemId)
            root._pendingConfirm = null
        }
    }
}
