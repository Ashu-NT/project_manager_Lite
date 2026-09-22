pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.organizations.sections 1.0 as OrgSections

// Orchestrator only: owns organization identity/lifecycle, per-tab
// state (page/search/filter/selection) and data fetching. Each tab's own
// markup lives in workspaces/organizations/sections/ -- see that folder's
// files for the Overview/Sites/Departments/Employees/Documents/Activity
// presentational components this page wires up below.
Item {
    id: detailRoot
    objectName: "adminOrganizationDetailPage"

    property var organization: ({})
    property var workspaceController: null
    property var platformCatalog: null
    property var breadcrumb: []
    property bool canWrite: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal navigateToDestination(string destinationId)

    signal relatedRecordRequested(string destinationId, string rowId)
    Connections {
        target: detailRoot.workspaceController
        function onSitesChanged() { detailRoot._refreshSites() }
        function onDepartmentsChanged() { detailRoot._refreshDepartments() }
        function onEmployeesChanged() { detailRoot._refreshEmployees() }
        function onDocumentsChanged() { detailRoot._refreshDocuments() }
    }

    readonly property var _orgState: (detailRoot.organization && detailRoot.organization.state)
        ? detailRoot.organization.state
        : ({})
    readonly property string _orgId: String(detailRoot.organization && detailRoot.organization.id
        ? detailRoot.organization.id
        : (detailRoot._orgState.organizationId || ""))
    readonly property string _orgTitle: String(detailRoot.organization && detailRoot.organization.title
        ? detailRoot.organization.title
        : "Organization")
    readonly property var _orgStatusLabelValue: detailRoot.organization ? detailRoot.organization.statusLabel : null
    readonly property string _orgStatus: (detailRoot._orgStatusLabelValue && typeof detailRoot._orgStatusLabelValue === "object")
        ? String(detailRoot._orgStatusLabelValue.label || "")
        : String(detailRoot._orgStatusLabelValue || "")
    readonly property string _orgStatusTone: (detailRoot._orgStatusLabelValue && typeof detailRoot._orgStatusLabelValue === "object")
        ? String(detailRoot._orgStatusLabelValue.tone || "neutral")
        : "neutral"
    readonly property string _orgSubtitle: String(detailRoot.organization && detailRoot.organization.subtitle
        ? detailRoot.organization.subtitle
        : "")
    readonly property string _orgCode: String(detailRoot._orgState.organizationCode || "")
    readonly property string _orgLocation: String(detailRoot._orgState.location || detailRoot._orgState.countryName || "")
    readonly property string _headerSubtitle: detailRoot._joinNonEmpty([detailRoot._orgCode, detailRoot._orgLocation], "  ·  ")
    readonly property bool _isActiveOrganization: detailRoot._orgState.status === "active"
    readonly property bool _isInactiveOrganization: detailRoot._orgState.status === "inactive"
    readonly property bool _isArchivedOrganization: detailRoot._orgState.status === "archived"

    // -- Actions -- a standalone [Edit] button plus a lifecycle "Actions ▾"
    // menu. The menu also repeats Edit organization ahead of a divider (per
    // the approved reference header design) so every command reachable from
    // this header is keyboard/menu-discoverable, not only the quick button.
    // Archived is a terminal state (see OrganizationService._require_valid_
    // organization_transition) -- no lifecycle items apply, so the whole
    // menu is omitted rather than shown with nothing useful in it.
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit organization", "icon": "edit", "enabled": detailRoot.canWrite },
            { "separator": true }
        ]
        if (detailRoot._isActiveOrganization) {
            items.push({ "id": "deactivate", "label": "Deactivate organization", "icon": "reject", "enabled": detailRoot.canWrite })
            items.push({ "id": "archive", "label": "Archive organization", "icon": "inventory", "danger": true, "enabled": detailRoot.canWrite })
        } else if (detailRoot._isInactiveOrganization) {
            items.push({ "id": "activate", "label": "Activate organization", "icon": "approve", "enabled": detailRoot.canWrite })
            items.push({ "id": "archive", "label": "Archive organization", "icon": "inventory", "danger": true, "enabled": detailRoot.canWrite })
        }
        return items
    }
    readonly property bool _showLifecycleMenu: detailRoot._isActiveOrganization || detailRoot._isInactiveOrganization

    property var _pendingConfirm: null

    function _requestLifecycleConfirm(action) {
        const name = detailRoot._orgTitle || "this organization"
        if (action === "deactivate") {
            detailRoot._pendingConfirm = {
                "action": "deactivate",
                "message": "Deactivate " + name + "?",
                "supportingText": name + " will no longer be available for new operational activity. " +
                    "Existing records and historical information will remain available according to permissions. " +
                    "If this organization is currently selected, the active organization context will be cleared."
            }
        } else if (action === "archive") {
            detailRoot._pendingConfirm = {
                "action": "archive",
                "message": "Archive " + name + "?",
                "supportingText": name + " will be removed from normal operational use and retained for historical " +
                    "reference. This action cannot be reversed through the normal Organization workspace. " +
                    "Existing business history will be preserved."
            }
        } else {
            return
        }
        _lifecycleConfirmDialog.open()
    }

    function _onLifecycleMenuAction(actionId) {
        if (actionId === "edit") {
            detailRoot.actionRequested("edit")
        } else if (actionId === "activate") {
            if (detailRoot.workspaceController) detailRoot.workspaceController.activateOrganization(detailRoot._orgId)
        } else if (actionId === "deactivate") {
            detailRoot._requestLifecycleConfirm("deactivate")
        } else if (actionId === "archive") {
            detailRoot._requestLifecycleConfirm("archive")
        }
    }

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Sites" },
        { "label": "Departments" },
        { "label": "Employees" },
        { "label": "Documents" },
        { "label": "Activity" }
    ]
    readonly property string _activeSectionLabel: {
        const section = detailRoot._sections[detailRoot.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        if (detailRoot._activeSectionLabel === "Overview") return detailRoot._orgSubtitle
        // Activity here is this organization's own history only -- distinct
        // from the tenant-wide Platform audit trail (Platform > Control).
        if (detailRoot._activeSectionLabel === "Activity") return "Activity for this organization only"
        return ""
    }
    // Identity, lifecycle badge, and Edit/Actions live in the persistent
    // header below (visible across every section) -- this per-section
    // toolbar only ever offers Refresh now.
    readonly property var _toolbarActions: [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
    // Blank persisted values ("") display as "-" rather than an empty label
    // or literal "None"/"null" -- the persisted value itself is untouched.
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
    }
    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    readonly property string _countryDisplay: {
        const code = String(detailRoot._orgState.countryCode || "").trim()
        if (code.length === 0) return ""
        const options = (detailRoot.workspaceController && detailRoot.workspaceController.organizationEditorOptions)
            ? (detailRoot.workspaceController.organizationEditorOptions.countryOptions || [])
            : []
        for (let i = 0; i < options.length; i += 1) {
            if (options[i].value === code) {
                return String(options[i].label || "") + " (" + code + ")"
            }
        }
        return code
    }

    readonly property var _basicInfoFields: [
        { "label": "Organization Name", "value": detailRoot._displayValue(detailRoot._orgState.displayName || detailRoot._orgTitle) },
        { "label": "Legal Name", "value": detailRoot._displayValue(detailRoot._orgState.legalName) },
        { "label": "Code", "value": detailRoot._displayValue(detailRoot._orgState.organizationCode) },
        { "label": "Registration Number", "value": detailRoot._displayValue(detailRoot._orgState.registrationNumber) },
        { "label": "Tax / VAT ID", "value": detailRoot._displayValue(detailRoot._orgState.taxId) },
        { "label": "Status", "value": detailRoot._orgStatus.length > 0 ? detailRoot._orgStatus : "Unknown" },
        { "label": "Time Zone", "value": detailRoot._displayValue(detailRoot._orgState.timezoneName) },
        { "label": "Base Currency", "value": detailRoot._displayValue(detailRoot._orgState.baseCurrency) }
    ]
    readonly property var _addressFields: [
        { "label": "Address Line 1", "value": detailRoot._displayValue(detailRoot._orgState.addressLine1) },
        { "label": "Address Line 2", "value": detailRoot._displayValue(detailRoot._orgState.addressLine2) },
        { "label": "Postal Code", "value": detailRoot._displayValue(detailRoot._orgState.postalCode) },
        { "label": "City", "value": detailRoot._displayValue(detailRoot._orgState.city) },
        { "label": "State / Region", "value": detailRoot._displayValue(detailRoot._orgState.stateRegion) },
        { "label": "Country", "value": detailRoot._countryDisplay.length > 0 ? detailRoot._countryDisplay : "—" }
    ]
    readonly property var _contactFields: [
        { "label": "Email", "value": detailRoot._displayValue(detailRoot._orgState.email) },
        { "label": "Phone", "value": detailRoot._displayValue(detailRoot._orgState.phone) },
        { "label": "Website", "value": detailRoot._displayValue(detailRoot._orgState.website) }
    ]

    // -- Real composed detail context (statistics + recent activity) -----
    // Fetched once per organization id, not per section activation, since
    // it backs Overview which is always the first section shown. Overview's
    // preview stays small/unbounded-filter-free by design -- the full,
    // paginated + filterable Activity tab is a separate state block below.
    property var _detailContext: ({ "statistics": ({}), "recentActivity": [] })

    // -- Operational calendar summary: the organization's one default
    // calendar (name/working week/time zone/holiday set), read-only --
    // full calendar editing stays exclusively in Platform > Calendars (see
    // OrganizationOverviewSection.qml). Fetched once per organization id,
    // like _detailContext above, and correctly scoped to _orgId regardless
    // of which organization is active in the caller's session.
    property var _calendarSummary: ({
        "hasCalendar": false, "calendarId": "", "calendarName": "",
        "workingWeekLabel": "No working days configured", "timeZone": "",
        "holidaySetLabel": "No holidays configured"
    })

    function _reloadDetailContext() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) {
            return
        }
        detailRoot._detailContext = detailRoot.workspaceController.organizationDetailContext(detailRoot._orgId)
        detailRoot._calendarSummary = detailRoot.workspaceController.organizationCalendarSummary(detailRoot._orgId)
    }

    function _openCalendarManagement() {
        if (detailRoot._calendarSummary.calendarId.length === 0) return
        detailRoot.relatedRecordRequested("calendars", detailRoot._calendarSummary.calendarId)
    }

    // -- Activity tab: a real, paginated + searchable + filterable business-
    // activity workspace for this organization (regardless of which
    // organization is active in the caller's session -- ActivityService's
    // organization-scoped reads already worked this way before this phase,
    // unlike Sites/Departments/Employees/Documents which needed a genuine
    // fix). Row activation opens the corresponding Site/Department/
    // Employee/Document's own nested Detail page.
    property int _activityPage: 1
    property int _activityPageSize: 25
    property string _activitySearch: ""
    property string _activityTypeFilter: ""
    property string _activityDateFilter: ""
    property var _activityCatalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    readonly property var _activityTypeFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "organization", "label": "Organization" },
        { "value": "site", "label": "Site" },
        { "value": "department", "label": "Department" },
        { "value": "employee", "label": "Employee" },
        { "value": "document", "label": "Document" }
    ]
    readonly property var _activityDateFilterOptions: [
        { "value": "", "label": "All time" },
        { "value": "today", "label": "Today" },
        { "value": "7d", "label": "Last 7 days" },
        { "value": "30d", "label": "Last 30 days" }
    ]

    function _refreshActivityPage() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) return
        detailRoot.workspaceController.clearMessages()
        detailRoot._activityCatalog = detailRoot.workspaceController.organizationActivityPage(
            detailRoot._orgId, detailRoot._activityPage, detailRoot._activityPageSize,
            detailRoot._activitySearch, detailRoot._activityTypeFilter, detailRoot._activityDateFilter
        )
    }

    // Routes an Activity row's activationState ({entityType, entityId}) to
    // that entity's own standalone workspace detail page (see
    // relatedRecordRequested above) -- the same destination every
    // Sites/Departments/Employees/Documents row activation uses.
    function _openEntityFromActivity(entityType, entityId) {
        if (entityType === "site") {
            detailRoot._openSiteDetail(entityId)
        } else if (entityType === "department") {
            detailRoot._openDepartmentDetail(entityId)
        } else if (entityType === "employee") {
            detailRoot._openEmployeeDetail(entityId)
        } else if (entityType === "document") {
            detailRoot._openDocumentDetail(entityId)
        }
    }

    onOrganizationChanged: {
        detailRoot._reloadDetailContext()
    }
    onActiveSectionIndexChanged: {
        if (detailRoot._activeSectionLabel === "Activity") {
            detailRoot._refreshActivityPage()
        }
        if (detailRoot._activeSectionLabel === "Sites") {
            detailRoot._refreshSites()
        }
        if (detailRoot._activeSectionLabel === "Departments") {
            detailRoot._refreshDepartments()
        }
        if (detailRoot._activeSectionLabel === "Employees") {
            detailRoot._refreshEmployees()
        }
        if (detailRoot._activeSectionLabel === "Documents") {
            detailRoot._refreshDocuments()
        }
    }
    Component.onCompleted: {
        detailRoot._reloadDetailContext()
        detailRoot._refreshSites()
        detailRoot._refreshDepartments()
        detailRoot._refreshEmployees()
        detailRoot._refreshDocuments()
        detailRoot._refreshActivityPage()
    }

    readonly property var _statistics: detailRoot._detailContext.statistics || ({})

    // -- Related Actions: real destinations only, gated by the same
    // Context Navigation Tree accessibility the sidebar itself uses. -----
    function _isDestinationAccessible(destinationId) {
        const groups = (detailRoot.platformCatalog && detailRoot.platformCatalog.contextNavigation) || []
        for (let g = 0; g < groups.length; g += 1) {
            const items = groups[g].items || []
            for (let i = 0; i < items.length; i += 1) {
                if (items[i].id === destinationId) {
                    return true
                }
            }
        }
        return false
    }
    readonly property var _relatedActions: {
        const candidates = [
            { "id": "sites", "label": "Manage Sites", "icon": "site" },
            { "id": "departments", "label": "Manage Departments", "icon": "department" },
            { "id": "employees", "label": "Manage Employees", "icon": "employee" },
            { "id": "documents", "label": "View Documents", "icon": "documents" }
        ]
        return candidates.filter(function(action) { return detailRoot._isDestinationAccessible(action.id) })
    }

    // -- Scoped routing: Related Actions and Key Statistics above are about
    // THIS organization's own Sites/Departments/Employees/Documents -- they
    // must switch this detail page's own tab, never navigate away to the
    // global, session-active-organization-only Platform workspace (which
    // would silently show a DIFFERENT organization's data whenever this
    // isn't the caller's active organization, and loses the "viewing this
    // organization" context even when it is). Only a destination with no
    // local tab of its own (none exist among the current candidates) falls
    // through to the bubbled-up navigateToDestination signal.
    readonly property var _sectionIndexByDestination: ({
        "sites": 1, "departments": 2, "employees": 3, "documents": 4
    })
    function _navigateFromOverview(destinationId) {
        const index = detailRoot._sectionIndexByDestination[destinationId]
        if (index !== undefined) {
            detailPage.scrollToSection(index)
            return
        }
        detailRoot.navigateToDestination(destinationId)
    }

    // -- Per-organization filtered catalogs (existing tenant-scoped lists,
    // filtered client-side by organizationId; a genuine per-organization
    // backend read is future work -- see Phase J report). -----------------
    function _filteredByOrg(catalog) {
        if (!catalog) return []
        const items = catalog.items || []
        const result = []
        for (let i = 0; i < items.length; i += 1) {
            const state = items[i].state || {}
            if (String(state.organizationId || "") === detailRoot._orgId) {
                result.push(items[i])
            }
        }
        return result
    }
    // -- Sites tab: a real, tenant-scoped + paginated Organization-Detail-
    // owned query (SiteService.list_sites_page_for_organization) -- unlike
    // Employees/Documents below, NOT a client-side filter of the global,
    // session-active-organization-only catalog. Works correctly regardless
    // of which organization is active in the caller's session, and remains
    // readable for inactive/archived organizations (see Phase K report). --
    property int _sitesPage: 1
    property int _sitesPageSize: 25
    property string _sitesSearch: ""
    property string _sitesStatusFilter: ""
    property var _sitesCatalog: ({
        "title": "Sites", "subtitle": "", "emptyState": "", "items": [],
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _sitesSelectedRowId: ""
    readonly property var _sitesStatusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _sitesColumns: [
        { "key": "title", "label": "Site", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "siteCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "location", "label": "Location", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "country", "label": "Country", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "timezoneName", "label": "Time Zone", "flex": 1, "minWidth": 130, "visible": false },
        { "key": "createdAt", "label": "Created", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "updatedAt", "label": "Updated", "flex": 1, "minWidth": 140, "visible": false }
    ]
    // Only your own currently-active organization can receive new sites
    // today (SiteService.create_site() -- an existing, unchanged domain
    // rule; this read-only phase does not add an explicit-organization
    // create path). Viewing another organization's sites stays fully
    // supported; creating into it from here does not.
    readonly property bool _isViewingActiveOrganization: detailRoot.platformCatalog
        && detailRoot.platformCatalog.organizationSwitcher
        && detailRoot.platformCatalog.organizationSwitcher.activeOrganizationId === detailRoot._orgId
    readonly property bool _canCreateSite: detailRoot.canWrite && detailRoot._isViewingActiveOrganization

    function _refreshSites() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) return
        detailRoot.workspaceController.clearMessages()
        detailRoot._sitesCatalog = detailRoot.workspaceController.organizationSitesPage(
            detailRoot._orgId, detailRoot._sitesPage, detailRoot._sitesPageSize,
            detailRoot._sitesSearch, detailRoot._sitesStatusFilter
        )
    }
    function _openSiteDetail(siteId) {
        detailRoot._sitesSelectedRowId = siteId
        detailRoot.relatedRecordRequested("sites", siteId)
    }

    // -- Departments tab: same tenant-scoped + paginated pattern as Sites
    // (DepartmentService.list_departments_page_for_organization) -- works
    // correctly regardless of which organization is active in the caller's
    // session, and remains readable for inactive/archived organizations.
    property int _departmentsPage: 1
    property int _departmentsPageSize: 25
    property string _departmentsSearch: ""
    property string _departmentsStatusFilter: ""
    property var _departmentsCatalog: ({
        "title": "Departments", "subtitle": "", "emptyState": "", "items": [],
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _departmentsSelectedRowId: ""
    readonly property var _departmentsStatusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _departmentsColumns: [
        { "key": "title", "label": "Department", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "departmentCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "siteName", "label": "Site", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "departmentType", "label": "Type", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "parentDepartmentName", "label": "Parent Department", "flex": 1, "minWidth": 150, "visible": false },
        { "key": "costCenterCode", "label": "Cost Center", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "createdAt", "label": "Created", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "updatedAt", "label": "Updated", "flex": 1, "minWidth": 140, "visible": false }
    ]
    // Only your own currently-active organization can receive new
    // departments today (DepartmentService.create_department() -- an
    // existing, unchanged domain rule; this read-only phase does not add
    // an explicit-organization create path). Viewing another organization's
    // departments stays fully supported; creating into it from here does not.
    readonly property bool _canCreateDepartment: detailRoot.canWrite && detailRoot._isViewingActiveOrganization

    function _refreshDepartments() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) return
        detailRoot.workspaceController.clearMessages()
        detailRoot._departmentsCatalog = detailRoot.workspaceController.organizationDepartmentsPage(
            detailRoot._orgId, detailRoot._departmentsPage, detailRoot._departmentsPageSize,
            detailRoot._departmentsSearch, detailRoot._departmentsStatusFilter
        )
    }
    function _openDepartmentDetail(departmentId) {
        detailRoot._departmentsSelectedRowId = departmentId
        detailRoot.relatedRecordRequested("departments", departmentId)
    }

    // -- Employees tab: same tenant-scoped + paginated pattern as Sites/
    // Departments (EmployeeService.list_employees_page_for_organization) --
    // works correctly regardless of which organization is active in the
    // caller's session, and remains readable for inactive/archived
    // organizations. Employee already denormalizes department/site NAMES
    // onto itself (no extra lookup joins needed, unlike Department's
    // site/parent-department name resolution).
    property int _employeesPage: 1
    property int _employeesPageSize: 25
    property string _employeesSearch: ""
    property string _employeesStatusFilter: ""
    property var _employeesCatalog: ({
        "title": "Employees", "subtitle": "", "emptyState": "", "items": [],
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _employeesSelectedRowId: ""
    readonly property var _employeesStatusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _employeesColumns: [
        { "key": "title", "label": "Employee", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "employeeCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "departmentName", "label": "Department", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "siteName", "label": "Site", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "employmentType", "label": "Employment Type", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "email", "label": "Email", "flex": 1, "minWidth": 160, "visible": false }
    ]
    // Only your own currently-active organization can receive new
    // employees today (EmployeeService.create_employee() -- an existing,
    // unchanged domain rule; this read-only phase does not add an
    // explicit-organization create path). Viewing another organization's
    // employees stays fully supported; creating into it from here does not.
    readonly property bool _canCreateEmployee: detailRoot.canWrite && detailRoot._isViewingActiveOrganization

    function _refreshEmployees() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) return
        detailRoot.workspaceController.clearMessages()
        detailRoot._employeesCatalog = detailRoot.workspaceController.organizationEmployeesPage(
            detailRoot._orgId, detailRoot._employeesPage, detailRoot._employeesPageSize,
            detailRoot._employeesSearch, detailRoot._employeesStatusFilter
        )
    }
    function _openEmployeeDetail(employeeId) {
        detailRoot._employeesSelectedRowId = employeeId
        detailRoot.relatedRecordRequested("employees", employeeId)
    }

    // -- Documents tab: same tenant-scoped + paginated pattern as Sites/
    // Departments/Employees for the LIST (DocumentService.
    // list_documents_page_for_organization) -- works correctly regardless
    // of which organization is active in the caller's session, and remains
    // readable for inactive/archived organizations. Row activation to the
    // full nested detail page is gated to only the ACTIVE organization --
    // see OrganizationDocumentsSection.qml's header comment for why.
    property int _documentsPage: 1
    property int _documentsPageSize: 25
    property string _documentsSearch: ""
    property string _documentsStatusFilter: ""
    property var _documentsCatalog: ({
        "title": "Documents", "subtitle": "", "emptyState": "", "items": [],
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _documentsSelectedRowId: ""
    readonly property var _documentsStatusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _documentsColumns: [
        { "key": "title", "label": "Document", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "documentCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "documentType", "label": "Type", "flex": 1, "minWidth": 120, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "businessVersionLabel", "label": "Version", "flex": 1, "minWidth": 100, "visible": false },
        { "key": "isCurrent", "label": "Current", "flex": 0, "minWidth": 90, "visible": false },
        { "key": "fileName", "label": "File", "flex": 1, "minWidth": 160, "visible": false }
    ]
    // Only your own currently-active organization can receive new documents
    // today (DocumentService.create_document() -- an existing, unchanged
    // domain rule; this read-only phase does not add an explicit-
    // organization create path). Viewing another organization's documents
    // stays fully supported; creating into it from here does not.
    readonly property bool _canCreateDocument: detailRoot.canWrite && detailRoot._isViewingActiveOrganization

    function _refreshDocuments() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) return
        detailRoot.workspaceController.clearMessages()
        detailRoot._documentsCatalog = detailRoot.workspaceController.organizationDocumentsPage(
            detailRoot._orgId, detailRoot._documentsPage, detailRoot._documentsPageSize,
            detailRoot._documentsSearch, detailRoot._documentsStatusFilter
        )
    }
    function _openDocumentDetail(documentId) {
        detailRoot._documentsSelectedRowId = documentId
        if (detailRoot.workspaceController) detailRoot.workspaceController.selectDocument(documentId)
        detailRoot.relatedRecordRequested("documents", documentId)
    }

    readonly property var _simpleColumns: [
        { key: "title", label: "Name", flex: 2, minWidth: 160, sortable: true, visible: true },
        { key: "subtitle", label: "Details", flex: 2, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status", flex: 0, minWidth: 90, sortable: false, visible: true, type: "status" }
    ]

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: detailRoot._orgTitle
        statusLabel: detailRoot._orgStatus
        statusTone: detailRoot._orgStatusTone
        subtitleLine: detailRoot._headerSubtitle
        breadcrumb: detailRoot.breadcrumb
        isBusy: detailRoot.busy
        showEdit: detailRoot.canWrite
        showDelete: false
        menuActions: detailRoot._showLifecycleMenu ? detailRoot._lifecycleMenuItems : []
        sections: detailRoot._sections

        onBackRequested: detailRoot.backRequested()
        onEditRequested: detailRoot.actionRequested("edit")
        onMenuActionTriggered: function(id) { detailRoot._onLifecycleMenuAction(id) }
        onSectionChanged: function(index) {
            detailRoot.activeSectionIndex = index
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : detailRoot.width
            requestedVisible: detailRoot.errorMessage.length > 0
            tone: "danger"
            message: detailRoot.errorMessage
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : detailRoot.width
            requestedVisible: detailRoot.feedbackMessage.length > 0 && detailRoot.errorMessage.length === 0
            tone: "success"
            message: detailRoot.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            id: _sectionToolbar
            detailPagePinned: true
            visible: detailRoot._activeSectionLabel !== "Sites"
                && detailRoot._activeSectionLabel !== "Departments"
                && detailRoot._activeSectionLabel !== "Employees"
                && detailRoot._activeSectionLabel !== "Documents"
                && detailRoot._activeSectionLabel !== "Activity"
            height: visible ? implicitHeight : 0
            width: parent ? parent.width : detailRoot.width
            title: detailRoot._activeSectionLabel
            subtitle: detailRoot._toolbarSubtitle
            busy: detailRoot.busy
            actions: detailRoot._toolbarActions
            onActionTriggered: function(actionId) {
                detailRoot.actionRequested(actionId)
            }
        }

        // -- Overview: two-region layout (main + summary rail) ------------
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading organization overview..."
                sourceComponent: Component {
                    OrgSections.OrganizationOverviewSection {
                        width: parent ? parent.width : 0
                        basicInfoFields: detailRoot._basicInfoFields
                        addressFields: detailRoot._addressFields
                        contactFields: detailRoot._contactFields
                        statistics: detailRoot._statistics
                        relatedActions: detailRoot._relatedActions
                        recentActivity: detailRoot._detailContext.recentActivity || []
                        isDestinationAccessible: detailRoot._isDestinationAccessible
                        calendarSummary: detailRoot._calendarSummary

                        onNavigateToDestination: function(destinationId) {
                            detailRoot._navigateFromOverview(destinationId)
                        }
                        onManageCalendarRequested: detailRoot._openCalendarManagement()
                        // scrollToSection (not a direct activeSectionIndex
                        // assignment) so the nav rail's own highlighted item
                        // stays in sync -- it owns that state and only
                        // updates it through this call or a rail click.
                        onViewAllActivityRequested: detailPage.scrollToSection(5)
                    }
                }
            }
        }

        // -- Sites: a real Organization-scoped management workspace (a
        // tenant-scoped backend read, not a client-side filter of the
        // global session-active-organization catalog -- see Phase K
        // report). Row activation opens the same AdminSiteDetailPage the
        // standalone Sites workspace uses. --------------------------------
        Item {
            // Unlike the other (still content-height-driven) sections
            // below, Sites fills the page's actual available viewport --
            // AdminEntityWorkspace is a full-panel component (fixed
            // pagination footer pinned to ITS bottom, internal DataTable
            // scrolling), not content that should size to its own row
            // count. Binding to a fixed pixel height here previously left
            // dead space below the pagination footer on tall viewports and
            // pushed the footer out of view entirely on short ones.
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 1
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: sitesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading sites..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    OrgSections.OrganizationSitesSection {
                        platformCatalog: detailRoot.platformCatalog
                        workspaceController: detailRoot.workspaceController
                        canWrite: detailRoot.canWrite
                        busy: detailRoot.busy
                        errorMessage: detailRoot.errorMessage
                        feedbackMessage: detailRoot.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: detailRoot._sitesCatalog
                        columns: detailRoot._sitesColumns
                        canCreate: detailRoot._canCreateSite
                        selectedRowId: detailRoot._sitesSelectedRowId
                        searchText: detailRoot._sitesSearch
                        statusFilterOptions: detailRoot._sitesStatusFilterOptions
                        statusFilter: detailRoot._sitesStatusFilter

                        onCreateRequested: detailRoot.actionRequested("create_site")
                        onRowSelected: function(id) { detailRoot._sitesSelectedRowId = id }
                        onRowActivated: function(id) { detailRoot._openSiteDetail(id) }
                        onRefreshRequested: detailRoot._refreshSites()
                        onSearchChanged: function(text) {
                            detailRoot._sitesSearch = text
                            detailRoot._sitesPage = 1
                            detailRoot._refreshSites()
                        }
                        onPageRequested: function(page) {
                            detailRoot._sitesPage = page
                            detailRoot._refreshSites()
                        }
                        onPageSizeRequested: function(pageSize) {
                            detailRoot._sitesPageSize = pageSize
                            detailRoot._sitesPage = 1
                            detailRoot._refreshSites()
                        }
                        onClearFiltersRequested: {
                            detailRoot._sitesSearch = ""
                            detailRoot._sitesStatusFilter = ""
                            detailRoot._sitesPage = 1
                            detailRoot._refreshSites()
                        }
                        onStatusFilterRequested: function(value) {
                            detailRoot._sitesStatusFilter = value
                            detailRoot._sitesPage = 1
                            detailRoot._refreshSites()
                        }
                    }
                }
            }
        }

        // -- Departments: same tenant-scoped, paginated Organization-Detail-
        // owned query pattern as Sites above. Row activation opens the same
        // AdminDepartmentDetailPage the standalone Departments workspace
        // uses. --------------------------------------------------------
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 2
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: departmentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading departments..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    OrgSections.OrganizationDepartmentsSection {
                        platformCatalog: detailRoot.platformCatalog
                        workspaceController: detailRoot.workspaceController
                        canWrite: detailRoot.canWrite
                        busy: detailRoot.busy
                        errorMessage: detailRoot.errorMessage
                        feedbackMessage: detailRoot.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: detailRoot._departmentsCatalog
                        columns: detailRoot._departmentsColumns
                        canCreate: detailRoot._canCreateDepartment
                        selectedRowId: detailRoot._departmentsSelectedRowId
                        searchText: detailRoot._departmentsSearch
                        statusFilterOptions: detailRoot._departmentsStatusFilterOptions
                        statusFilter: detailRoot._departmentsStatusFilter

                        onCreateRequested: detailRoot.actionRequested("create_department")
                        onRowSelected: function(id) { detailRoot._departmentsSelectedRowId = id }
                        onRowActivated: function(id) { detailRoot._openDepartmentDetail(id) }
                        onRefreshRequested: detailRoot._refreshDepartments()
                        onSearchChanged: function(text) {
                            detailRoot._departmentsSearch = text
                            detailRoot._departmentsPage = 1
                            detailRoot._refreshDepartments()
                        }
                        onPageRequested: function(page) {
                            detailRoot._departmentsPage = page
                            detailRoot._refreshDepartments()
                        }
                        onPageSizeRequested: function(pageSize) {
                            detailRoot._departmentsPageSize = pageSize
                            detailRoot._departmentsPage = 1
                            detailRoot._refreshDepartments()
                        }
                        onClearFiltersRequested: {
                            detailRoot._departmentsSearch = ""
                            detailRoot._departmentsStatusFilter = ""
                            detailRoot._departmentsPage = 1
                            detailRoot._refreshDepartments()
                        }
                        onStatusFilterRequested: function(value) {
                            detailRoot._departmentsStatusFilter = value
                            detailRoot._departmentsPage = 1
                            detailRoot._refreshDepartments()
                        }
                    }
                }
            }
        }

        // -- Employees: same tenant-scoped, paginated Organization-Detail-
        // owned query pattern as Sites/Departments above. Row activation
        // opens the same AdminEmployeeDetailPage the standalone Employees
        // workspace uses. --------------------------------------------------
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 3
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: employeesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading employees..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    OrgSections.OrganizationEmployeesSection {
                        platformCatalog: detailRoot.platformCatalog
                        workspaceController: detailRoot.workspaceController
                        canWrite: detailRoot.canWrite
                        busy: detailRoot.busy
                        errorMessage: detailRoot.errorMessage
                        feedbackMessage: detailRoot.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: detailRoot._employeesCatalog
                        columns: detailRoot._employeesColumns
                        canCreate: detailRoot._canCreateEmployee
                        selectedRowId: detailRoot._employeesSelectedRowId
                        searchText: detailRoot._employeesSearch
                        statusFilterOptions: detailRoot._employeesStatusFilterOptions
                        statusFilter: detailRoot._employeesStatusFilter
                        onCreateRequested: detailRoot.actionRequested("create_employee")
                        onRowSelected: function(id) { detailRoot._employeesSelectedRowId = id }
                        onRowActivated: function(id) { detailRoot._openEmployeeDetail(id) }
                        onRefreshRequested: detailRoot._refreshEmployees()
                        onSearchChanged: function(text) {
                            detailRoot._employeesSearch = text
                            detailRoot._employeesPage = 1
                            detailRoot._refreshEmployees()
                        }
                        onPageRequested: function(page) {
                            detailRoot._employeesPage = page
                            detailRoot._refreshEmployees()
                        }
                        onPageSizeRequested: function(pageSize) {
                            detailRoot._employeesPageSize = pageSize
                            detailRoot._employeesPage = 1
                            detailRoot._refreshEmployees()
                        }
                        onClearFiltersRequested: {
                            detailRoot._employeesSearch = ""
                            detailRoot._employeesStatusFilter = ""
                            detailRoot._employeesPage = 1
                            detailRoot._refreshEmployees()
                        }
                        onStatusFilterRequested: function(value) {
                            detailRoot._employeesStatusFilter = value
                            detailRoot._employeesPage = 1
                            detailRoot._refreshEmployees()
                        }
                    }
                }
            }
        }

        // -- Documents: same tenant-scoped, paginated Organization-Detail-
        // owned query pattern as Sites/Departments/Employees above for the
        // LIST. Row activation to the full nested detail page is gated to
        // only the ACTIVE organization -- see
        // OrganizationDocumentsSection.qml's header comment for why.
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 4
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: documentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 4
                keepLoaded: true
                loadingMessage: "Loading documents..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    OrgSections.OrganizationDocumentsSection {
                        platformCatalog: detailRoot.platformCatalog
                        workspaceController: detailRoot.workspaceController
                        canWrite: detailRoot.canWrite
                        busy: detailRoot.busy
                        errorMessage: detailRoot.errorMessage
                        feedbackMessage: detailRoot.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: detailRoot._documentsCatalog
                        columns: detailRoot._documentsColumns
                        canCreate: detailRoot._canCreateDocument
                        isViewingActiveOrganization: detailRoot._isViewingActiveOrganization
                        selectedRowId: detailRoot._documentsSelectedRowId
                        searchText: detailRoot._documentsSearch
                        statusFilterOptions: detailRoot._documentsStatusFilterOptions
                        statusFilter: detailRoot._documentsStatusFilter

                        onCreateRequested: detailRoot.actionRequested("create_document")
                        onRowSelected: function(id) { detailRoot._documentsSelectedRowId = id }
                        onRowActivated: function(id) { detailRoot._openDocumentDetail(id) }
                        onRefreshRequested: detailRoot._refreshDocuments()
                        onSearchChanged: function(text) {
                            detailRoot._documentsSearch = text
                            detailRoot._documentsPage = 1
                            detailRoot._refreshDocuments()
                        }
                        onPageRequested: function(page) {
                            detailRoot._documentsPage = page
                            detailRoot._refreshDocuments()
                        }
                        onPageSizeRequested: function(pageSize) {
                            detailRoot._documentsPageSize = pageSize
                            detailRoot._documentsPage = 1
                            detailRoot._refreshDocuments()
                        }
                        onClearFiltersRequested: {
                            detailRoot._documentsSearch = ""
                            detailRoot._documentsStatusFilter = ""
                            detailRoot._documentsPage = 1
                            detailRoot._refreshDocuments()
                        }
                        onStatusFilterRequested: function(value) {
                            detailRoot._documentsStatusFilter = value
                            detailRoot._documentsPage = 1
                            detailRoot._refreshDocuments()
                        }
                    }
                }
            }
        }

        // -- Activity: this organization's own history only -- a distinct,
        // narrower scope than the tenant-wide Platform audit trail (Platform
        // > Control > Audit). A real, paginated + searchable + filterable
        // business-activity workspace (see terminology-glossary.md "Recent
        // Activity" / "Audit") -- separate from Overview's small, bounded
        // Recent Activity preview above.
        Item {
            // Same viewport-fill pattern as Sites/Departments/Employees/
            // Documents (see their own height fix in the Phase K reports):
            // a fixed pixel/content-driven height here previously left
            // dead space below the pagination footer on tall viewports.
            // OrganizationActivitySection fills this height itself and
            // scrolls the feed internally, keeping the toolbar/pagination
            // pinned to the top/bottom of the actual available space.
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 5
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 5
                keepLoaded: true
                loadingMessage: "Loading organization activity..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    OrgSections.OrganizationActivitySection {
                        width: parent ? parent.width : 0
                        height: Math.max(420, detailPage.contentViewportHeight)
                        catalog: detailRoot._activityCatalog
                        busy: detailRoot.busy
                        searchText: detailRoot._activitySearch
                        typeFilterOptions: detailRoot._activityTypeFilterOptions
                        typeFilter: detailRoot._activityTypeFilter
                        dateFilterOptions: detailRoot._activityDateFilterOptions
                        dateFilter: detailRoot._activityDateFilter

                        onRefreshRequested: detailRoot._refreshActivityPage()
                        onSearchChanged: function(text) {
                            detailRoot._activitySearch = text
                            detailRoot._activityPage = 1
                            detailRoot._refreshActivityPage()
                        }
                        onTypeFilterRequested: function(value) {
                            detailRoot._activityTypeFilter = value
                            detailRoot._activityPage = 1
                            detailRoot._refreshActivityPage()
                        }
                        onDateFilterRequested: function(value) {
                            detailRoot._activityDateFilter = value
                            detailRoot._activityPage = 1
                            detailRoot._refreshActivityPage()
                        }
                        onPageRequested: function(page) {
                            detailRoot._activityPage = page
                            detailRoot._refreshActivityPage()
                        }
                        onPageSizeRequested: function(pageSize) {
                            detailRoot._activityPageSize = pageSize
                            detailRoot._activityPage = 1
                            detailRoot._refreshActivityPage()
                        }
                        onItemActivated: function(item) {
                            const activation = item ? item.activationState : null
                            if (activation && activation.entityType && activation.entityId) {
                                detailRoot._openEntityFromActivity(String(activation.entityType), String(activation.entityId))
                            }
                        }
                    }
                }
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: _lifecycleConfirmDialog
        title: "Confirm"
        confirmLabel: detailRoot._pendingConfirm && detailRoot._pendingConfirm.action === "archive"
            ? "Archive organization" : "Deactivate organization"
        confirmIcon: detailRoot._pendingConfirm && detailRoot._pendingConfirm.action === "archive" ? "inventory" : "reject"
        confirmDanger: true
        message: detailRoot._pendingConfirm ? String(detailRoot._pendingConfirm.message || "") : ""
        supportingText: detailRoot._pendingConfirm ? String(detailRoot._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = detailRoot._pendingConfirm
            if (!pending || !detailRoot.workspaceController) return
            if (pending.action === "deactivate") {
                detailRoot.workspaceController.deactivateOrganization(detailRoot._orgId)
            } else if (pending.action === "archive") {
                detailRoot.workspaceController.archiveOrganization(detailRoot._orgId)
            }
            detailRoot._pendingConfirm = null
        }
    }
}
