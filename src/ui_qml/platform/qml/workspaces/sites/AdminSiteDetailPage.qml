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
    property var employeeCatalog: ({ "items": [], "emptyState": "No employees are available yet." })
    property var employeeColumns: []
    property var departmentColumns: []
    property var siteCalendarAssignment: ({})
    property var calendarSourceChain: []
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
    readonly property string _supportingText: String(root.site && root.site.supportingText ? root.site.supportingText : "")
    readonly property string _metaText: String(root.site && root.site.metaText ? root.site.metaText : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property string _statusTone: root._isActive ? "success" : "neutral"
    readonly property bool _pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
    readonly property string _siteId: String(root._state.siteId || root._state.id || root.site.id || "")
    readonly property string _organizationId: String(root._state.organizationId || "")
    readonly property bool _hasCalendarAssignment: String(root.siteCalendarAssignment && root.siteCalendarAssignment.assignmentId ? root.siteCalendarAssignment.assignmentId : "").length > 0

    // -- Departments tab: explicit site_id-scoped backend query
    // (DepartmentService.list_departments(site_id=...)), not a client-side
    // filter of the shared, session-active-organization-only catalog --
    // works correctly regardless of which organization/site is active in
    // the caller's session.
    property var _departmentsCatalog: ({ "items": [], "emptyState": "No departments are available yet." })
    readonly property var _departmentRows: root._departmentsCatalog.items || []
    function _refreshDepartments() {
        if (root._siteId.length === 0 || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            root._departmentsCatalog = ({ "items": [], "emptyState": "No departments are available yet." })
            return
        }
        root._departmentsCatalog = root.platformCatalog.adminWorkspace.departmentsForSite(root._siteId)
    }

    readonly property var _employeeRows: {
        // Depend on employeeCatalog so this re-fetches whenever the shared
        // employee catalog changes (create/update/activate/deactivate
        // elsewhere), but query only this site's rows via SQL rather than
        // a full-org client-side filter.
        const _refreshToken = root.employeeCatalog
        const siteId = root._siteId
        if (siteId.length === 0 || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return []
        }
        const result = root.platformCatalog.adminWorkspace.employeesForSite(siteId)
        return (result && result.items) || []
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
            { "label": "Departments", "count": root._departmentRows.length },
            { "label": "Employees", "count": root._employeeRows.length }
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
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":
            return root._subtitle
        case "Departments":
            return "Shared departments mapped to this site through the platform department master."
        case "Employees":
            return "Employees aligned to this site through the shared employee master."
        case "Projects":
            return "Project Management project/site alignment delegated to the PM module."
        case "Calendar":
            return "Site-level calendar assignment and working schedule inherited from the global calendar hierarchy."
        case "Documents":
            return "Site-scoped document governance stays in the shared document workspace."
        case "Activity":
            return "Activity for this site only"
        default:
            return ""
        }
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "edit", "label": "Edit", "icon": "edit", "enabled": root.canWrite },
                { "id": "toggle_active", "label": root._isActive ? "Set Inactive" : "Set Active", "icon": "approve", "enabled": root.canWrite },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Departments") {
            return [
                { "id": "create_department", "label": "New Department", "icon": "add", "enabled": root.canWrite },
                { "id": "show_departments", "label": "Open Departments", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Employees") {
            return [
                { "id": "create_employee", "label": "New Employee", "icon": "add", "enabled": root.canManageEmployees },
                { "id": "show_employees", "label": "Open Employees", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Calendar") {
            return [
                { "id": "assign_calendar", "label": root._hasCalendarAssignment ? "Change Calendar" : "Assign Calendar", "icon": "calendar", "enabled": root.canManageCalendar },
                { "id": "clear_calendar_assignment", "label": "Clear Assignment", "icon": "delete", "danger": true, "enabled": root._hasCalendarAssignment && root.canManageCalendar },
                { "id": "open_calendar_mgmt", "label": "Calendar Management", "icon": "chevron_right" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Documents") {
            return [
                { "id": "show_documents", "label": "Open Documents", "icon": "chevron_right" }
            ]
        }
        return [
            { "id": "refresh", "label": "Refresh", "icon": "refresh" }
        ]
    }
    readonly property var _overviewFields: [
        { "label": "Site Code", "value": root._state.siteCode },
        { "label": "Display Name", "value": root._state.name || root.site.title },
        { "label": "Site Type", "value": root._state.siteType },
        { "label": "Status", "value": root._status },
        { "label": "Version", "value": root._state.version },
        { "label": "Active", "value": root._isActive },
        { "label": "City", "value": root._state.city },
        { "label": "Country", "value": root._state.country },
        { "label": "Timezone", "value": root._state.timezoneName },
        { "label": "Currency", "value": root._state.currencyCode }
    ]
    readonly property string _overviewDescription: String(
        root._state.description || root._state.notes
        || "This shared platform site anchors downstream PM and inventory records without duplicating those module-owned operational structures here."
    )

    // -- Scoped routing: "Open Departments"/"Open Employees" are about THIS
    // site's own child data, which already has a full local tab -- they
    // must switch this detail page's own tab (never navigate away to the
    // global, session-active-organization-only Platform workspace, which
    // would silently show a DIFFERENT site's/org's data whenever this isn't
    // the caller's active context). Departments is always index 1 and
    // Employees always index 2 in _sections above (Projects/Calendar/
    // Documents/Activity only ever appear after them). Calendar/Projects/
    // Documents have no local tab with this capability, so those stay
    // genuine cross-workspace navigation (handled by SitesWorkspacePage.qml).
    readonly property var _sectionIndexByDestination: ({
        "show_departments": 1, "show_employees": 2
    })
    function _handleToolbarAction(actionId) {
        const index = root._sectionIndexByDestination[actionId]
        if (index !== undefined) {
            detailPage.scrollToSection(index)
            return
        }
        root.actionRequested(actionId)
    }

    function _tableHeightForCount(count) {
        const visibleRows = Math.max(1, Math.min(count, 8))
        return Theme.AppTheme.headerHeight + (visibleRows * Theme.AppTheme.normalRowHeight) + Theme.AppTheme.spacingLg
    }

    onSiteChanged: {
        root._refreshDepartments()
        root._refreshActivityPage()
    }
    Component.onCompleted: {
        root._refreshDepartments()
        root._refreshActivityPage()
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        isBusy: root.busy
        showEdit: false
        showDelete: false
        sections: root._sections

        onBackRequested: root.backRequested()
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
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                root._handleToolbarAction(actionId)
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
                        overviewFields: root._overviewFields
                        status: root._status
                        statusTone: root._statusTone
                        supportingText: root._supportingText
                        metaText: root._metaText
                        description: root._overviewDescription
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Departments" ? departmentsLoader.implicitHeight : 0
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
                sourceComponent: Component {
                    SiteSections.SiteDepartmentsSection {
                        rows: root._departmentRows
                        columns: root.departmentColumns
                        tableHeight: root._tableHeightForCount(root._departmentRows.length)
                        loading: root.busy
                        onRowActivated: function(rowId) {
                            root.relatedRowActivated("departments", rowId)
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Employees" ? employeesLoader.implicitHeight : 0
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
                sourceComponent: Component {
                    SiteSections.SiteEmployeesSection {
                        rows: root._employeeRows
                        columns: root.employeeColumns
                        loading: root.busy
                        tableHeight: root._tableHeightForCount(root._employeeRows.length)
                        onRowActivated: function(rowId) {
                            root.relatedRowActivated("employees", rowId)
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
