pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import workspaces.sites.sections 1.0 as SiteSections

// Orchestrator only: owns site identity/lifecycle, per-tab state (page/
// search/filter) and data fetching. Each tab's own markup lives in
// workspaces/sites/sections/ -- see that folder's files for the
// Overview/Departments/Employees/Projects/Calendar/Documents/Activity
// presentational components this page wires up below.
Item {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var site: ({})
    property var breadcrumb: []
    property var employeeCatalog: ({ "items": [], "emptyState": "No employees are available yet." })
    property var employeeColumns: []
    property var departmentColumns: []
    property var siteCalendarAssignment: ({})
    property var calendarSourceChain: []
    property var siteCalendarSummary: ({
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

    readonly property var _state: (root.site && root.site.state) ? root.site.state : ({})
    readonly property string _title: String(root.site && root.site.title ? root.site.title : "Site")
    readonly property var _statusLabelValue: root.site ? root.site.statusLabel : null
    readonly property string _status: (root._statusLabelValue && typeof root._statusLabelValue === "object")
        ? String(root._statusLabelValue.label || "")
        : String(root._statusLabelValue || "")
    readonly property string _subtitle: String(root.site && root.site.subtitle ? root.site.subtitle : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property string _statusTone: root._isActive ? "success" : "neutral"
    readonly property bool _pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
    readonly property string _siteId: String(root._state.siteId || root._state.id || root.site.id || "")
    readonly property string _organizationId: String(root._state.organizationId || "")
    readonly property bool _hasCalendarAssignment: String(root.siteCalendarAssignment && root.siteCalendarAssignment.assignmentId ? root.siteCalendarAssignment.assignmentId : "").length > 0

    readonly property string _siteCode: String(root._state.siteCode || "")
    readonly property string _siteType: String(root._state.siteType || "")
    readonly property string _siteLocation: String(root._state.location || "")
    readonly property string _headerSubtitle: root._joinNonEmpty([root._siteCode, root._siteType, root._siteLocation], "  ·  ")
    readonly property bool _isActiveSite: root._state.status === "active"
    readonly property bool _isInactiveSite: root._state.status === "inactive"

    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
    }

    // -- Header lifecycle menu: full 3-state (Active/Inactive/Archived),
    // matching AdminOrganizationDetailPage's own header menu exactly.
    // Archived is terminal -- the menu is simply empty then. Mutations
    // bubble up via actionRequested() to SitesWorkspacePage.qml's
    // handleDetailAction, which owns the shared confirm dialog (this page
    // has no direct workspaceController of its own).
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit site", "icon": "edit", "enabled": root.canWrite },
            { "separator": true }
        ]
        if (root._isActiveSite) {
            items.push({ "id": "deactivate", "label": "Deactivate site", "icon": "reject", "enabled": root.canWrite })
            items.push({ "id": "archive", "label": "Archive site", "icon": "inventory", "danger": true, "enabled": root.canWrite })
        } else if (root._isInactiveSite) {
            items.push({ "id": "activate", "label": "Activate site", "icon": "approve", "enabled": root.canWrite })
            items.push({ "id": "archive", "label": "Archive site", "icon": "inventory", "danger": true, "enabled": root.canWrite })
        }
        return items
    }
    readonly property bool _showLifecycleMenu: root._isActiveSite || root._isInactiveSite

    // -- Departments tab: explicit site_id-scoped, paginated backend query
    // (DepartmentService.list_departments_page_for_organization(site_id=...)) --
    // works correctly regardless of which organization/site is active in
    // the caller's session.
    property int _departmentsPage: 1
    property int _departmentsPageSize: 25
    property string _departmentsSearch: ""
    property string _departmentsStatusFilter: ""
    property var _departmentsCatalog: ({
        "title": "Departments", "items": [], "emptyState": "No departments assigned to this site.",
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _departmentsSelectedRowId: ""
    function _refreshDepartments() {
        if (root._siteId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._departmentsCatalog = root.platformCatalog.adminWorkspace.departmentsForSitePage(
            root._siteId, root._organizationId, root._departmentsPage, root._departmentsPageSize,
            root._departmentsSearch, root._departmentsStatusFilter
        )
    }
    readonly property int _departmentCount: root._departmentsCatalog.totalCount || 0

    // -- Employees tab: same site_id-scoped, paginated pattern as
    // Departments above.
    property int _employeesPage: 1
    property int _employeesPageSize: 25
    property string _employeesSearch: ""
    property string _employeesStatusFilter: ""
    property string _employeesDepartmentFilter: ""
    property var _employeesCatalog: ({
        "title": "Employees", "items": [], "emptyState": "This site does not currently have employees assigned.",
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _employeesSelectedRowId: ""
    function _refreshEmployees() {
        if (root._siteId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._employeesCatalog = root.platformCatalog.adminWorkspace.employeesForSitePage(
            root._siteId, root._organizationId, root._employeesPage, root._employeesPageSize,
            root._employeesSearch, root._employeesStatusFilter, root._employeesDepartmentFilter
        )
    }
    readonly property int _employeeCount: root._employeesCatalog.totalCount || 0
    // Real department options for this site only -- reuses the already-
    // fetched Departments tab data (no extra query) rather than the full
    // organization's department list.
    readonly property var _employeesDepartmentFilterOptions: {
        const options = [{ "value": "", "label": "All Departments" }]
        const rows = root._departmentsCatalog.items || []
        for (let i = 0; i < rows.length; i += 1) {
            const state = rows[i].state || {}
            const id = String(state.departmentId || state.id || rows[i].id || "")
            if (id.length === 0) continue
            options.push({ "value": id, "label": String(rows[i].title || state.name || id) })
        }
        return options
    }

    // -- Overview: bounded (~5 item) recent activity, distinct from the
    // full paginated Activity tab's own state below.
    property var _recentActivity: []
    function _refreshRecentActivity() {
        if (root._siteId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            root._recentActivity = []
            return
        }
        root._recentActivity = root.platformCatalog.adminWorkspace.siteActivity(root._siteId, root._organizationId) || []
    }

    // -- Activity tab: this site's own paginated, searchable business-
    // activity history -- distinct from the tenant-wide Platform audit
    // trail the previous "Audit" stub tab pointed to.
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
        if (root._siteId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._activityCatalog = root.platformCatalog.adminWorkspace.siteActivityPage(
            root._siteId, root._organizationId, root._activityPage, root._activityPageSize,
            root._activitySearch, root._activityDateFilter
        )
    }

    readonly property var _sections: {
        const sections = [
            { "label": "Overview" },
            { "label": "Departments", "count": root._departmentCount },
            { "label": "Employees", "count": root._employeeCount }
        ]
        if (root._pmEnabled) {
            sections.push({ "label": "Projects" })
        }
        sections.push({ "label": "Calendar" })
        sections.push({ "label": "Documents" })
        sections.push({ "label": "Activity" })
        return sections
    }
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
            return "Site-level calendar assignment and working schedule."
        default:
            return ""
        }
    }
    // Identity, lifecycle badge, and Edit/Actions live in the persistent
    // header below (visible across every section) -- the per-section
    // toolbar is only shown for Overview (Refresh) and Calendar (its own
    // assignment actions); Departments/Employees/Activity own their own
    // embedded toolbar+refresh, and Projects/Documents have nothing to
    // refresh, so the outer toolbar is hidden there entirely (avoids the
    // duplicate-Refresh problem the previous Activity implementation had).
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
        }
        if (root._activeSectionLabel === "Calendar") {
            return [
                { "id": "assign_calendar", "label": root._hasCalendarAssignment ? "Change Calendar" : "Assign Site Calendar", "icon": "calendar", "enabled": root.canManageCalendar },
                { "id": "clear_calendar_assignment", "label": "Remove Override", "icon": "delete", "danger": true, "enabled": root._hasCalendarAssignment && root.canManageCalendar },
                { "id": "open_calendar_mgmt", "label": root._hasCalendarAssignment ? "Open Calendar" : "Open Calendar Management", "icon": "chevron_right" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        return []
    }
    readonly property bool _showSectionToolbar: root._activeSectionLabel === "Overview" || root._activeSectionLabel === "Calendar"

    // -- Overview: Basic Information / Physical Address / Operational
    // Context field groups, plus Key Statistics / Related Actions sourced
    // from real, already-fetched (no extra N+1) site-scoped data.
    readonly property var _basicInfoFields: [
        { "label": "Site Name", "value": root._displayValue(root._state.name || root.site.title) },
        { "label": "Site Code", "value": root._displayValue(root._state.siteCode) },
        { "label": "Site Type", "value": root._displayValue(root._state.siteType) },
        { "label": "Organization", "value": root._displayValue(root._state.organizationName) },
        { "label": "Description", "value": root._displayValue(root._state.description) }
    ]
    readonly property var _addressFields: [
        { "label": "Address Line 1", "value": root._displayValue(root._state.addressLine1) },
        { "label": "Address Line 2", "value": root._displayValue(root._state.addressLine2) },
        { "label": "Postal Code", "value": root._displayValue(root._state.postalCode) },
        { "label": "City", "value": root._displayValue(root._state.city) },
        { "label": "State / Region", "value": root._displayValue(root._state.region) },
        { "label": "Country", "value": root._displayValue(root._state.country) }
    ]
    readonly property var _operationalContextFields: [
        { "label": "Time Zone", "value": root._displayValue(root._state.timezoneName) },
        { "label": "Currency", "value": root._displayValue(root._state.currencyCode) }
    ]
    readonly property var _statistics: ({
        "departmentCount": root._departmentCount,
        "employeeCount": root._employeeCount
    })
    readonly property var _relatedActions: [
        { "id": "departments", "label": "Manage Departments", "icon": "department" },
        { "id": "employees", "label": "Manage Employees", "icon": "employee" }
    ]

    function _navigateFromOverview(destinationId) {
        const label = destinationId === "departments" ? "Departments" : destinationId === "employees" ? "Employees" : ""
        const index = label.length > 0 ? root._indexOfSection(label) : -1
        if (index >= 0) {
            detailPage.scrollToSection(index)
            return
        }
        root.actionRequested(destinationId)
    }

    onSiteChanged: {
        root._refreshDepartments()
        root._refreshEmployees()
        root._refreshActivityPage()
        root._refreshRecentActivity()
    }
    Component.onCompleted: {
        root._refreshDepartments()
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
        menuActions: root._showLifecycleMenu ? root._lifecycleMenuItems : []
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
                loadingMessage: "Loading site overview..."
                sourceComponent: Component {
                    SiteSections.SiteOverviewSection {
                        basicInfoFields: root._basicInfoFields
                        addressFields: root._addressFields
                        operationalContextFields: root._operationalContextFields
                        statistics: root._statistics
                        relatedActions: root._relatedActions
                        recentActivity: root._recentActivity
                        calendarSummary: root.siteCalendarSummary

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
            implicitHeight: root._activeSectionLabel === "Departments"
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: departmentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Departments"
                keepLoaded: true
                loadingMessage: "Loading site departments..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    SiteSections.SiteDepartmentsSection {
                        platformCatalog: root.platformCatalog
                        canWrite: root.canWrite
                        busy: root.busy
                        errorMessage: root.errorMessage
                        feedbackMessage: root.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: root._departmentsCatalog
                        columns: root.departmentColumns
                        canCreate: root.canWrite
                        selectedRowId: root._departmentsSelectedRowId
                        searchText: root._departmentsSearch
                        statusFilterOptions: [
                            { "value": "", "label": "All" },
                            { "value": "active", "label": "Active" },
                            { "value": "inactive", "label": "Inactive" }
                        ]
                        statusFilter: root._departmentsStatusFilter

                        onCreateRequested: root.actionRequested("create_department")
                        onRowSelected: function(id) { root._departmentsSelectedRowId = id }
                        onRowActivated: function(id) { root.relatedRowActivated("departments", id) }
                        onRefreshRequested: root._refreshDepartments()
                        onSearchChanged: function(text) {
                            root._departmentsSearch = text
                            root._departmentsPage = 1
                            root._refreshDepartments()
                        }
                        onPageRequested: function(page) {
                            root._departmentsPage = page
                            root._refreshDepartments()
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._departmentsPageSize = pageSize
                            root._departmentsPage = 1
                            root._refreshDepartments()
                        }
                        onClearFiltersRequested: {
                            root._departmentsSearch = ""
                            root._departmentsStatusFilter = ""
                            root._departmentsPage = 1
                            root._refreshDepartments()
                        }
                        onStatusFilterRequested: function(value) {
                            root._departmentsStatusFilter = value
                            root._departmentsPage = 1
                            root._refreshDepartments()
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
                loadingMessage: "Loading site employees..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    SiteSections.SiteEmployeesSection {
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
                        departmentFilterOptions: root._employeesDepartmentFilterOptions
                        departmentFilter: root._employeesDepartmentFilter

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
                            root._employeesDepartmentFilter = ""
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                        onStatusFilterRequested: function(value) {
                            root._employeesStatusFilter = value
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                        onDepartmentFilterRequested: function(value) {
                            root._employeesDepartmentFilter = value
                            root._employeesPage = 1
                            root._refreshEmployees()
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Projects" ? projectsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: projectsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Projects"
                keepLoaded: true
                loadingMessage: "Loading site project guidance..."
                sourceComponent: Component {
                    SiteSections.SiteProjectsSection {}
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
                loadingMessage: "Loading site calendar..."
                sourceComponent: Component {
                    SiteSections.SiteCalendarSection {
                        entityId: root._siteId
                        entityLabel: root._title
                        assignedCalendar: root.siteCalendarAssignment
                        sourceChain: root.calendarSourceChain
                        effectiveCalendarSummary: root.siteCalendarSummary
                        busy: root.busy
                        onAssignCalendarRequested: root.actionRequested("assign_calendar")
                        onOpenCalendarManagementRequested: root.actionRequested("open_calendar_mgmt")
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Documents" ? documentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: documentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Documents"
                keepLoaded: true
                loadingMessage: "Loading site document guidance..."
                sourceComponent: Component {
                    SiteSections.SiteDocumentsSection {}
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
                loadingMessage: "Loading site activity..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    SiteSections.SiteActivitySection {
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
