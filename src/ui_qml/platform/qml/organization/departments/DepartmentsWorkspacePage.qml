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

// R4: Departments as a standalone Platform destination. Same shape as
// SitesWorkspacePage: related-employees list (relatedRowActivated) and
// calendar-assignment context, reused verbatim from the facade's existing
// wiring, fixed to entityType "department".
AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    signal navigateToDestination(string destinationId)
    signal relatedRecordRequested(string destinationId, string rowId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var departmentCatalog: root.workspaceController
        ? root.workspaceController.departments
        : ({ "title": "Departments", "subtitle": "", "emptyState": "", "items": [] })
    property var employeeCatalog: root.workspaceController
        ? root.workspaceController.employees
        : ({ "title": "Employees", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _columns: [
        { key: "title",       label: "Name",        flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "siteName",    label: "Site",        flex: 2.4, minWidth: 180, sortable: true, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Cost Center", flex: 2, minWidth: 120, sortable: false, visible: true, hideBelow: Theme.AppTheme.compactContentBreakpoint }
    ]
    readonly property var _employeeColumns: [
        { key: "title",       label: "Name",             flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Job Title", flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "departmentName", label: "Department",    flex: 2.4, minWidth: 180, sortable: true, visible: true },
        { key: "siteName",    label: "Site",             flex: 2.2, minWidth: 160, sortable: true, visible: true },
        { key: "statusLabel", label: "Status",           flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Employment",       flex: 3, minWidth: 160, sortable: false, visible: true }
    ]

    property string selectedRowId: ""
    property bool detailOpen: false
    property var _pendingConfirm: null

    function requestToggleActive() {
        const item = root._selectedItem
        if (!item || !root.workspaceController) return
        if (item.isActive) {
            root._pendingConfirm = {
                "itemId": root.selectedRowId,
                "message": "Deactivate " + String(item.title || "this department") + "?",
                "supportingText": "It will be marked inactive."
            }
            confirmDialog.open()
        } else {
            root.workspaceController.toggleDepartmentActive(root.selectedRowId)
        }
    }

    // RBAC: gates create/edit/set-active buttons for the department's own
    // mutations, plus the related-record "New Employee" and calendar
    // assignment actions surfaced from the department detail page -- a
    // client-side UX optimization mirroring PlatformNavigation's own
    // destination gate; the backend enforces these permissions
    // independently regardless.
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
        const items = root.departmentCatalog.items || []
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
        if (actionId === "assign_calendar") {
            const item = root._selectedItem || {}
            const state = item.state || {}
            const entityId = String(state.departmentId || state.id || item.id || "")
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
        if (actionId === "open_calendar_mgmt") { root.navigateToDestination("calendars"); return }
        if (actionId === "create_employee") { dialogHostLoader.invoke("openEmployeeCreate"); return }
        if (actionId === "show_employees") { root.navigateToDestination("employees"); return }
        if (actionId === "refresh") { if (root.workspaceController) root.workspaceController.refresh(); return }
        if (actionId === "show_audit") { root.navigateToDestination("control_audit"); return }
        if (actionId === "edit") { root.openEdit(id); return }
        if (actionId === "toggle_active" && root.workspaceController) { root.requestToggleActive(); return }
    }

    title: "Departments"
    subtitle: String(root.departmentCatalog.subtitle || "")

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0
            visible: !root.detailOpen

            PlatformComponents.AdminEntityWorkspace {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Departments"
                entityLabel: "Department"
                catalog: root.departmentCatalog
                catalogModel: root.workspaceController ? root.workspaceController.departmentsTableModel : null
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId

                onCreateRequested: dialogHostLoader.invoke("openDepartmentCreate")
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
                AdminDepartmentDetailPage {
                    platformCatalog: root.platformCatalog
                    department: root._selectedItem || ({})
                    canWrite: root._canWrite
                    canManageEmployees: root._canManageEmployees
                    canManageCalendar: root._canManageCalendar
                    employeeCatalog: root.employeeCatalog
                    employeeColumns: root._employeeColumns
                    deptCalendarAssignment: root._calendarContext.assignedCalendar || ({})
                    calendarSourceChain: root._calendarContext.sourceChain || []
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
            root.workspaceController.toggleDepartmentActive(pending.itemId)
            root._pendingConfirm = null
        }
    }
}
