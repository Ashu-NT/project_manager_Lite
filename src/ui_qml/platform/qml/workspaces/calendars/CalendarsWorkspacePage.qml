pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import App.Theme 1.0 as Theme
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents
import Platform.Dialogs 1.0 as AdminDialogs
import "sections/CalendarsColumnConfig.js" as ColumnConfig

// Calendars as a standalone Platform destination. Same list+inspector+
// generic actionId-dispatch detail shell as Site/Department/Employee/Party;
// AdminCalendarDetailPage owns its own data fetching (Overview/Calendar/
// Assignments/Activity), this page only opens the shared create/edit/
// exception/recurring-rule dialogs and the calendar-lifecycle confirmation.
// No "Toggle" secondary action here: PlatformAdminWorkspaceController has
// no toggleCalendarActive method at all (confirmed) -- showing one would
// be a dead, unwireable button, so it's omitted rather than faked.
AppLayouts.WorkspaceFrame {
    id: root
    objectName: "calendarsWorkspacePage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    signal navigateToDestination(string destinationId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var calendarCatalog: root.workspaceController
        ? root.workspaceController.calendars
        : ({ "title": "Calendars", "subtitle": "", "emptyState": "", "items": [] })

    readonly property string _tableId: "platform.calendars.table"
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

    readonly property var _statusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _typeFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "GLOBAL", "label": "Organization" },
        { "value": "SITE", "label": "Site" },
        { "value": "DEPARTMENT", "label": "Department" },
        { "value": "EMPLOYEE", "label": "Employee" },
        { "value": "PROJECT", "label": "Project" },
        { "value": "RESOURCE", "label": "Resource" }
    ]

    property string selectedRowId: ""
    property bool detailOpen: false

    // RBAC: gates create/edit buttons -- a client-side UX optimization; the
    // backend enforces "calendar.manage" independently regardless.
    readonly property bool _canWrite: root.platformCatalog
        ? root.platformCatalog.hasPermission("calendar.manage")
        : true

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.calendarCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _inspectorGroups: {
        const item = root._selectedItem
        if (!item) return []
        const state = item.state || {}
        return [
            {
                "title": "Identity",
                "rows": [
                    { "label": "Code", "value": String(state.code || "") },
                    { "label": "Type", "value": String(state.typeLabel || "") }
                ]
            },
            {
                "title": "Schedule",
                "rows": [
                    { "label": "Time Zone", "value": String(state.timeZone || "") },
                    { "label": "Working Week", "value": String(state.workingWeekLabel || "") }
                ]
            },
            {
                "title": "Usage",
                "rows": [
                    { "label": "Organization Default", "value": state.isDefault === true ? "Yes" : "No" },
                    { "label": "Assignments", "value": String(state.usageLabel || "") }
                ]
            },
            {
                "title": "Validity",
                "rows": [
                    { "label": "Effective From", "value": String(state.effectiveFrom || "") },
                    { "label": "Effective To", "value": String(state.effectiveTo || "") }
                ]
            }
        ]
    }

    // Reflects backend capability state (isDefault) rather than
    // re-deriving the Organization-default protection rule in QML --
    // the backend independently enforces CALENDAR_DEFAULT_CANNOT_DEACTIVATE
    // regardless of what this menu offers.
    readonly property var _inspectorLifecycleMenuItems: {
        const item = root._selectedItem
        if (!item) return []
        const state = item.state || {}
        const isActive = state.isActive === true
        const isDefault = state.isDefault === true
        const items = []
        if (isActive) {
            if (!isDefault) {
                items.push({ "id": "deactivate", "label": "Deactivate calendar", "icon": "reject", "enabled": root._canWrite })
            }
        } else {
            items.push({ "id": "activate", "label": "Activate calendar", "icon": "approve", "enabled": root._canWrite })
        }
        if (!isDefault) {
            items.push({ "id": "delete", "label": "Delete calendar", "icon": "delete", "danger": true, "enabled": root._canWrite })
        }
        return items
    }

    property var _pendingConfirm: null

    function _requestLifecycleConfirm(action, calendarId, calendarName) {
        const name = calendarName || "this calendar"
        if (action === "deactivate") {
            root._pendingConfirm = {
                "action": "deactivate", "calendarId": calendarId,
                "message": "Deactivate " + name + "?",
                "supportingText": name + " will no longer be available for new assignments. Existing assignments and historical data remain available."
            }
        } else if (action === "delete") {
            root._pendingConfirm = {
                "action": "delete", "calendarId": calendarId,
                "message": "Delete " + name + "?",
                "supportingText": "This calendar will be permanently removed. This action cannot be undone."
            }
        } else {
            return
        }
        _lifecycleConfirmDialog.open()
    }

    function _performLifecycleAction(actionId, calendarId, calendarName) {
        if (!root.workspaceController) return
        if (actionId === "activate") {
            root.workspaceController.updatePlatformCalendar({ "calendarId": calendarId, "isActive": true })
        } else if (actionId === "deactivate" || actionId === "delete") {
            root._requestLifecycleConfirm(actionId, calendarId, calendarName)
        }
    }

    function _onInspectorMenuAction(actionId) {
        if (!root._selectedItem) return
        root._performLifecycleAction(actionId, root.selectedRowId, root._selectedItem.title)
    }

    readonly property string _calendarId: {
        const item = root._selectedItem
        const state = item && item.state ? item.state : {}
        return String(state.calendarId || state.id || (item ? item.id : "") || "")
    }

    function _itemById(itemId) {
        const items = root.calendarCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openCalendarEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    function handleDetailAction(actionId) {
        const id = root.selectedRowId
        const item = root._selectedItem
        if (actionId === "edit") { root.openEdit(id); return }
        if (actionId === "activate" || actionId === "deactivate" || actionId === "delete") {
            root._performLifecycleAction(actionId, id, item ? item.title : "")
            return
        }
        if (actionId === "add_exception") { dialogHostLoader.invoke("openCalendarExceptionCreate", root._calendarId); return }
        if (actionId.indexOf("add_exception:") === 0) {
            const prefillDate = actionId.substring("add_exception:".length)
            dialogHostLoader.invoke("openCalendarExceptionCreate", root._calendarId, prefillDate)
            return
        }
        if (actionId === "add_recurring") { dialogHostLoader.invoke("openCalendarRecurringEventCreate", root._calendarId); return }
        if (actionId === "refresh") { if (root.workspaceController) root.workspaceController.refresh(); return }
    }

    title: "Calendars"
    subtitle: String(root.calendarCatalog.subtitle || "")
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
                sectionTitle: "Calendars"
                entityLabel: "Calendar"
                catalog: root.calendarCatalog
                catalogModel: root.workspaceController ? root.workspaceController.calendarsTableModel : null
                tableId: root._tableId
                columns: root._columns
                canCreate: root._canWrite
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId
                showSearch: true
                searchText: root.workspaceController ? root.workspaceController.calendarSearchText : ""

                AppControls.ComboBox {
                    Layout.preferredWidth: 150
                    model: root._statusFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.calendarStatusFilter : ""
                        for (let i = 0; i < root._statusFilterOptions.length; i += 1) {
                            if (root._statusFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setCalendarStatusFilter(String(currentValue || ""))
                    }
                }

                AppControls.ComboBox {
                    Layout.preferredWidth: 160
                    model: root._typeFilterOptions
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: {
                        const filter = root.workspaceController ? root.workspaceController.calendarTypeFilter : ""
                        for (let i = 0; i < root._typeFilterOptions.length; i += 1) {
                            if (root._typeFilterOptions[i].value === filter) return i
                        }
                        return 0
                    }
                    onActivated: {
                        if (root.workspaceController) root.workspaceController.setCalendarTypeFilter(String(currentValue || ""))
                    }
                }

                onCreateRequested: dialogHostLoader.invoke("openCalendarCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onSearchChanged: function(text) {
                    if (root.workspaceController) root.workspaceController.setCalendarSearchText(text)
                }
                onClearFiltersRequested: {
                    if (!root.workspaceController) return
                    root.workspaceController.setCalendarSearchText("")
                    root.workspaceController.setCalendarStatusFilter("")
                    root.workspaceController.setCalendarTypeFilter("")
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
                // "Open Details" is the primary, full-width action; "Edit"
                // and the lifecycle "Actions ▾" menu share the secondary
                // row beneath it -- same hierarchy as Site/Department.
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
                AdminCalendarDetailPage {
                    workspaceController: root.workspaceController
                    calendar: root._selectedItem || ({})
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
        id: _lifecycleConfirmDialog
        title: "Confirm"
        confirmLabel: root._pendingConfirm && root._pendingConfirm.action === "delete" ? "Delete calendar" : "Deactivate calendar"
        confirmIcon: root._pendingConfirm && root._pendingConfirm.action === "delete" ? "delete" : "reject"
        confirmDanger: true
        message: root._pendingConfirm ? String(root._pendingConfirm.message || "") : ""
        supportingText: root._pendingConfirm ? String(root._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = root._pendingConfirm
            if (!pending || !root.workspaceController) return
            if (pending.action === "deactivate") {
                root.workspaceController.updatePlatformCalendar({ "calendarId": pending.calendarId, "isActive": false })
            } else if (pending.action === "delete") {
                root.workspaceController.deletePlatformCalendar(pending.calendarId)
                if (root.selectedRowId === pending.calendarId) root.selectedRowId = ""
            }
            root._pendingConfirm = null
        }
    }
}
