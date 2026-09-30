pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Shell.Context 1.0 as ShellContexts
import workspaces.departments.sections 1.0 as DepartmentSections

// Orchestrator only: owns department identity/lifecycle, per-tab state
// (page/search/filter) and data fetching. Each tab's own markup lives in
// workspaces/departments/sections/ -- see that folder's files for the
// Overview/Employees/Calendar/Activity presentational components this page
// wires up below. Modernized to the same shape as AdminSiteDetailPage.qml;
// final section set is exactly Overview/Employees/Calendar/Activity -- no
// Users/Projects/Documents/Audit tabs (see Related Actions for optional
// cross-module navigation instead).
Item {
    id: root
    objectName: "adminDepartmentDetailPage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var department: ({})
    property var breadcrumb: []
    // Bubbled straight down from DepartmentsWorkspacePage.qml -> the shell's
    // own selectRoute(), the same cross-module navigation abstraction PM's
    // own dashboard cards already use in the opposite direction. Never
    // imported by Platform business logic; just a plain passed-through
    // reference.
    property ShellContexts.ShellContext shellModel
    property var employeeColumns: []
    property var deptCalendarAssignment: ({})
    property var calendarSourceChain: []
    property var deptCalendarSummary: ({
        "hasCalendar": false, "calendarId": "", "calendarName": "", "source": "",
        "workingWeekLabel": "No working days configured", "timeZone": "", "holidaySetLabel": "No holidays configured"
    })
    property bool canWrite: true
    property bool canManageEmployees: true
    property bool canManageCalendar: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal relatedRowActivated(string sectionId, string rowId)

    readonly property var _state: (root.department && root.department.state) ? root.department.state : ({})
    readonly property string _title: String(root.department && root.department.title ? root.department.title : "Department")
    readonly property var _statusLabelValue: root.department ? root.department.statusLabel : null
    readonly property string _status: (root._statusLabelValue && typeof root._statusLabelValue === "object")
        ? String(root._statusLabelValue.label || "")
        : String(root._statusLabelValue || "")
    readonly property string _subtitle: String(root.department && root.department.subtitle ? root.department.subtitle : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property string _statusTone: root._isActive ? "success" : "neutral"
    readonly property bool _pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
    readonly property string _departmentId: String(root._state.departmentId || root._state.id || root.department.id || "")
    readonly property string _organizationId: String(root._state.organizationId || "")
    readonly property bool _hasCalendarAssignment: String(root.deptCalendarAssignment && root.deptCalendarAssignment.assignmentId ? root.deptCalendarAssignment.assignmentId : "").length > 0

    readonly property string _departmentCode: String(root._state.departmentCode || "")
    readonly property string _departmentType: String(root._state.departmentType || "")
    readonly property string _siteName: String(root._state.siteName || "")
    readonly property string _headerSubtitle: root._joinNonEmpty([root._departmentCode, root._departmentType, root._siteName], "  ·  ")

    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
    }

    // -- Header lifecycle menu: Department's own 2-state lifecycle (Active/
    // Inactive only -- no Archive; see activate_department/
    // deactivate_department, a distinct, guarded command pair, not the
    // generic profile update). Mutations bubble up via actionRequested() to
    // DepartmentsWorkspacePage.qml's handleDetailAction, which owns the
    // shared confirm dialog (this page has no direct workspaceController of
    // its own).
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit department", "icon": "edit", "enabled": root.canWrite },
            { "separator": true }
        ]
        if (root._isActive) {
            items.push({ "id": "deactivate", "label": "Deactivate department", "icon": "reject", "enabled": root.canWrite })
        } else {
            items.push({ "id": "activate", "label": "Activate department", "icon": "approve", "enabled": root.canWrite })
        }
        return items
    }

    property int _employeesPage: 1
    property int _employeesPageSize: 25
    property string _employeesSearch: ""
    property string _employeesStatusFilter: ""
    property var _employeesCatalog: ({
        "title": "Employees", "items": [], "emptyState": "This department does not currently have employees assigned.",
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _employeesSelectedRowId: ""
    function _refreshEmployees() {
        if (root._departmentId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._employeesCatalog = root.platformCatalog.adminWorkspace.employeesForDepartmentPage(
            root._departmentId, root._organizationId, root._employeesPage, root._employeesPageSize,
            root._employeesSearch, root._employeesStatusFilter
        )
    }
    // `totalCount` is the whole-organization total; `filteredTotal` is
    // scoped to this department.
    readonly property int _employeeCount: root._employeesCatalog.filteredTotal || 0

    // -- Overview: bounded (~5 item) recent activity, distinct from the
    // full paginated Activity tab's own state below.
    property var _recentActivity: []
    function _refreshRecentActivity() {
        if (root._departmentId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            root._recentActivity = []
            return
        }
        root._recentActivity = root.platformCatalog.adminWorkspace.departmentActivity(root._departmentId, root._organizationId) || []
    }

    // -- Activity tab: this department's own paginated, searchable
    // business-activity history.
    property int _activityPage: 1
    property int _activityPageSize: 25
    property string _activitySearch: ""
    property string _activityDateFilter: ""
    property var _activityCatalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    readonly property var _activityDateFilterOptions: [
        { "value": "", "label": "All time" },
        { "value": "today", "label": "Today" },
        { "value": "7d", "label": "Last 7 days" },
        { "value": "30d", "label": "Last 30 days" }
    ]
    function _refreshActivityPage() {
        if (root._departmentId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._activityCatalog = root.platformCatalog.adminWorkspace.departmentActivityPage(
            root._departmentId, root._organizationId, root._activityPage, root._activityPageSize,
            root._activitySearch, root._activityDateFilter
        )
    }

    // Users/Projects/Documents/Audit are not tabs -- see Related Actions
    // for optional cross-module navigation instead.
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Employees", "count": root._employeeCount },
        { "label": "Calendar" },
        { "label": "Activity" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    function _indexOfSection(label) {
        for (let i = 0; i < root._sections.length; i += 1) {
            if (root._sections[i].label === label) return i
        }
        return -1
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":
            return root._subtitle
        case "Calendar":
            return "Working calendar and availability for this department."
        default:
            return ""
        }
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
        }
        if (root._activeSectionLabel === "Calendar") {
            return [
                { "id": "assign_calendar", "label": root._hasCalendarAssignment ? "Change Calendar" : "Assign Department Override", "icon": "calendar", "enabled": root.canManageCalendar },
                { "id": "clear_calendar_assignment", "label": "Remove Override", "icon": "delete", "danger": true, "enabled": root._hasCalendarAssignment && root.canManageCalendar },
                { "id": "open_calendar_mgmt", "label": root._hasCalendarAssignment ? "Open Calendar" : "Open Calendar Management", "icon": "chevron_right" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        return []
    }
    readonly property bool _showSectionToolbar: root._activeSectionLabel === "Overview" || root._activeSectionLabel === "Calendar"

    // Lifecycle status lives in the header/toolbar badge only -- never
    // duplicated here as a second "Status"/"Active" row. IDs are never
    // shown as primary values; Site/Parent Department/Head of Department
    // all resolve to their real display names (already provided by the
    // presenter). Description is included only when it actually has
    // content -- no placeholder row for a field that is simply unset.
    readonly property var _basicInfoFields: {
        const fields = [
            { "label": "Department Name", "value": root._displayValue(root._state.name || root.department.title) },
            { "label": "Department Code", "value": root._displayValue(root._state.departmentCode) },
            { "label": "Department Type", "value": root._displayValue(root._state.departmentType) },
            { "label": "Organization", "value": root._displayValue(root._state.organizationName) }
        ]
        const description = String(root._state.description || "").trim()
        if (description.length > 0) {
            fields.push({ "label": "Description", "value": description })
        }
        return fields
    }
    readonly property var _structureFields: [
        { "label": "Site", "value": root._displayValue(root._state.siteName) },
        { "label": "Head of Department", "value": root._displayValue(root._state.headOfDepartmentDisplay) },
        { "label": "Parent Department", "value": root._displayValue(root._state.parentDepartmentName) }
    ]
    // Notes is a plain field here (with the same "—" placeholder every
    // other Overview field uses when unset) rather than its own
    // always-visible card with generic filler text -- there is no such
    // thing as an empty "Operational Notes" shell to render.
    readonly property var _operationalContextFields: [
        { "label": "Cost Center Code", "value": root._displayValue(root._state.costCenterCode) },
        { "label": "Notes", "value": root._displayValue(root._state.notes) }
    ]
    readonly property var _statistics: ({
        "employeeCount": root._employeeCount
    })
    // Manage Employees/Manage Calendar are context-preserving local
    // actions (open this department's own tab). Open Project Management/
    // Open Documents are optional EXTERNAL actions -- real cross-module
    // navigation, not a substitute for a scoped tab. Documents' navigation
    // always works (a real Platform-internal destination); Project
    // Management is only offered when the module is actually enabled.
    readonly property var _relatedActions: {
        const actions = [
            { "id": "employees", "label": "Manage Employees", "icon": "employee" },
            { "id": "calendar", "label": "Manage Calendar", "icon": "calendar" }
        ]
        if (root._pmEnabled) {
            actions.push({ "id": "open_project_management", "label": "Open Project Management", "icon": "project" })
        }
        actions.push({ "id": "open_documents", "label": "Open Documents", "icon": "documents" })
        return actions
    }

    function _navigateFromOverview(destinationId) {
        const label = destinationId === "employees" ? "Employees" : destinationId === "calendar" ? "Calendar" : ""
        const index = label.length > 0 ? root._indexOfSection(label) : -1
        if (index >= 0) {
            detailPage.scrollToSection(index)
            return
        }
        root.actionRequested(destinationId)
    }

    onDepartmentChanged: {
        root._refreshEmployees()
        root._refreshActivityPage()
        root._refreshRecentActivity()
    }
    Component.onCompleted: {
        root._refreshEmployees()
        root._refreshActivityPage()
        root._refreshRecentActivity()
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        statusLabel: root._status
        statusTone: root._statusTone
        subtitleLine: root._headerSubtitle
        breadcrumb: root.breadcrumb
        isBusy: root.busy
        showEdit: root.canWrite
        showDelete: false
        menuActions: root._lifecycleMenuItems
        sections: root._sections

        onBackRequested: root.backRequested()
        onEditRequested: root.actionRequested("edit")
        onMenuActionTriggered: function(id) { root.actionRequested(id) }
        onSectionChanged: function(index) {
            root.activeSectionIndex = index
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            detailPagePinned: true
            visible: root._showSectionToolbar
            height: visible ? implicitHeight : 0
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                root.actionRequested(actionId)
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading department overview..."
                sourceComponent: Component {
                    DepartmentSections.DepartmentOverviewSection {
                        basicInfoFields: root._basicInfoFields
                        structureFields: root._structureFields
                        operationalContextFields: root._operationalContextFields
                        statistics: root._statistics
                        relatedActions: root._relatedActions
                        recentActivity: root._recentActivity
                        calendarSummary: root.deptCalendarSummary

                        onNavigateToDestination: function(destinationId) {
                            root._navigateFromOverview(destinationId)
                        }
                        onManageCalendarRequested: {
                            const index = root._indexOfSection("Calendar")
                            if (index >= 0) detailPage.scrollToSection(index)
                        }
                        onViewAllActivityRequested: {
                            const index = root._indexOfSection("Activity")
                            if (index >= 0) detailPage.scrollToSection(index)
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Employees"
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: employeesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Employees"
                keepLoaded: true
                loadingMessage: "Loading department employees..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    DepartmentSections.DepartmentEmployeesSection {
                        platformCatalog: root.platformCatalog
                        canWrite: root.canManageEmployees
                        busy: root.busy
                        errorMessage: root.errorMessage
                        feedbackMessage: root.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: root._employeesCatalog
                        columns: root.employeeColumns
                        canCreate: root.canManageEmployees
                        selectedRowId: root._employeesSelectedRowId
                        searchText: root._employeesSearch
                        statusFilterOptions: [
                            { "value": "", "label": "All" },
                            { "value": "active", "label": "Active" },
                            { "value": "inactive", "label": "Inactive" }
                        ]
                        statusFilter: root._employeesStatusFilter

                        onCreateRequested: root.actionRequested("create_employee")
                        onRowSelected: function(id) { root._employeesSelectedRowId = id }
                        onRowActivated: function(id) { root.relatedRowActivated("employees", id) }
                        onRefreshRequested: root._refreshEmployees()
                        onSearchChanged: function(text) {
                            root._employeesSearch = text
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                        onPageRequested: function(page) {
                            root._employeesPage = page
                            root._refreshEmployees()
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._employeesPageSize = pageSize
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                        onClearFiltersRequested: {
                            root._employeesSearch = ""
                            root._employeesStatusFilter = ""
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                        onStatusFilterRequested: function(value) {
                            root._employeesStatusFilter = value
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Calendar" ? calendarLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: calendarLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Calendar"
                keepLoaded: true
                loadingMessage: "Loading department calendar..."
                sourceComponent: Component {
                    DepartmentSections.DepartmentCalendarSection {
                        entityId: root._departmentId
                        entityLabel: root._title
                        assignedCalendar: root.deptCalendarAssignment
                        sourceChain: root.calendarSourceChain
                        effectiveCalendarSummary: root.deptCalendarSummary
                        busy: root.busy
                        onAssignCalendarRequested: root.actionRequested("assign_calendar")
                        onOpenCalendarManagementRequested: root.actionRequested("open_calendar_mgmt")
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Activity"
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: activityLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Activity"
                keepLoaded: true
                loadingMessage: "Loading department activity..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    DepartmentSections.DepartmentActivitySection {
                        width: parent ? parent.width : 0
                        height: Math.max(420, detailPage.contentViewportHeight)
                        catalog: root._activityCatalog
                        busy: root.busy
                        searchText: root._activitySearch
                        dateFilterOptions: root._activityDateFilterOptions
                        dateFilter: root._activityDateFilter

                        onRefreshRequested: root._refreshActivityPage()
                        onSearchChanged: function(text) {
                            root._activitySearch = text
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                        onDateFilterRequested: function(value) {
                            root._activityDateFilter = value
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                        onPageRequested: function(page) {
                            root._activityPage = page
                            root._refreshActivityPage()
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._activityPageSize = pageSize
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                    }
                }
            }
        }
    }
}
