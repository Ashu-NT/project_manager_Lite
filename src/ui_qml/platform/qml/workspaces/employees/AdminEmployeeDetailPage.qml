pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Shell.Context 1.0 as ShellContexts
import workspaces.employees.sections 1.0 as EmployeeSections
import "sections/EmployeeDocumentsColumns.js" as DocumentColumns

// Orchestrator only: owns employee identity/lifecycle, per-tab state
// (page/search/filter) and data fetching. Each tab's own markup lives in
// workspaces/employees/sections/ -- see that folder's files for the
// Overview/Calendar/Documents/Activity presentational components this page
// wires up below. Modernized to the same shape as AdminDepartmentDetailPage.qml;
// final section set is Overview/Calendar/Documents/Activity -- no User
// Account/Assignments/Timesheets/Certifications/Audit tabs (see Related
// Actions for optional cross-module navigation, and Overview's System
// Access card for the real Employee<->User relationship). Documents is the
// first real production consumer of the generic Platform DocumentLink
// capability -- see employee_documents.py and
// employee_documents_presenter.py.
Item {
    id: root
    objectName: "adminEmployeeDetailPage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var employee: ({})
    property var breadcrumb: []
    // Bubbled straight down from EmployeesWorkspacePage.qml -> the shell's
    // own selectRoute(), the same cross-module navigation abstraction
    // Department's/Site's own Related Actions already use. Never imported
    // by Platform business logic; just a plain passed-through reference.
    property ShellContexts.ShellContext shellModel
    property var empCalendarAssignment: ({})
    property var calendarSourceChain: []
    property var empCalendarSummary: ({
        "hasCalendar": false, "calendarId": "", "calendarName": "", "source": "",
        "workingWeekLabel": "No working days configured", "timeZone": "", "holidaySetLabel": "No holidays configured"
    })
    // { "linked": bool, "identity": "", "isActive": bool }
    property var systemAccess: ({ "linked": false, "identity": "", "isActive": false })
    property bool canWrite: true              // employee.manage -- edit/lifecycle
    property bool canManageSystemAccess: true // employee.manage AND auth.manage -- link/unlink User account
    property bool canManageCalendar: true     // task.manage -- assign/clear calendar
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal relatedRowActivated(string sectionId, string rowId)

    readonly property var _state: (root.employee && root.employee.state) ? root.employee.state : ({})
    readonly property string _title: String(root.employee && root.employee.title ? root.employee.title : "Employee")
    readonly property var _statusLabelValue: root.employee ? root.employee.statusLabel : null
    readonly property string _status: (root._statusLabelValue && typeof root._statusLabelValue === "object")
        ? String(root._statusLabelValue.label || "")
        : String(root._statusLabelValue || "")
    readonly property string _subtitle: String(root.employee && root.employee.subtitle ? root.employee.subtitle : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property string _statusTone: root._isActive ? "success" : "neutral"
    readonly property string _employeeId: String(root._state.employeeId || root._state.id || root.employee.id || "")
    readonly property string _organizationId: String(root._state.organizationId || "")
    readonly property bool _hasCalendarAssignment: String(root.empCalendarAssignment && root.empCalendarAssignment.assignmentId ? root.empCalendarAssignment.assignmentId : "").length > 0

    readonly property string _employeeCode: String(root._state.employeeCode || "")
    readonly property string _jobTitle: String(root._state.jobTitle || "")
    readonly property string _departmentName: String(root._state.departmentName || "")
    readonly property string _headerSubtitle: root._joinNonEmpty([root._employeeCode, root._jobTitle, root._departmentName], "  ·  ")

    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
    }

    // -- Header lifecycle menu: Employee's own 2-state lifecycle (Active/
    // Inactive only -- no Archive; see activate_employee/deactivate_
    // employee, a distinct, guarded command pair, not the generic profile
    // update). Mutations bubble up via actionRequested() to
    // EmployeesWorkspacePage.qml's handleDetailAction, which owns the
    // shared confirm dialog (this page has no direct workspaceController of
    // its own).
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit employee", "icon": "edit", "enabled": root.canWrite },
            { "separator": true }
        ]
        if (root._isActive) {
            items.push({ "id": "deactivate", "label": "Deactivate employee", "icon": "reject", "enabled": root.canWrite })
        } else {
            items.push({ "id": "activate", "label": "Activate employee", "icon": "approve", "enabled": root.canWrite })
        }
        return items
    }

    // -- Overview: bounded (~5 item) recent activity, distinct from the
    // full paginated Activity tab's own state below.
    property var _recentActivity: []
    function _refreshRecentActivity() {
        if (root._employeeId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            root._recentActivity = []
            return
        }
        root._recentActivity = root.platformCatalog.adminWorkspace.employeeActivity(root._employeeId, root._organizationId) || []
    }

    // -- Activity tab: this employee's own paginated, searchable
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
        if (root._employeeId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._activityCatalog = root.platformCatalog.adminWorkspace.employeeActivityPage(
            root._employeeId, root._organizationId, root._activityPage, root._activityPageSize,
            root._activitySearch, root._activityDateFilter
        )
    }

    // -- Documents tab: this employee's own paginated, searchable, linked
    // Documents -- the first real production consumer of the generic
    // Platform DocumentLink capability (see Phase 1-3 of the Documents
    // workstream). Mirrors the Activity tab's own state shape exactly.
    readonly property var _documentsColumns: DocumentColumns.columns()
    property int _documentsPage: 1
    property int _documentsPageSize: 25
    property string _documentsSearch: ""
    property string _documentsStatusFilter: ""
    property string _documentsTypeFilter: ""
    property var _documentsCatalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    readonly property var _documentsStatusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _documentsTypeFilterOptions: {
        const options = root.platformCatalog ? (root.platformCatalog.adminWorkspace.employeeDocumentTypeOptions() || []) : []
        return [{ "value": "", "label": "All Types" }].concat(options)
    }
    function _refreshDocumentsPage() {
        if (root._employeeId.length === 0 || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._documentsCatalog = root.platformCatalog.adminWorkspace.employeeDocumentsPage(
            root._employeeId, root._documentsPage, root._documentsPageSize,
            root._documentsSearch, root._documentsStatusFilter, root._documentsTypeFilter
        )
    }
    // Unlinking is a relationship removal handled entirely on this page
    // (via platformCatalog, already passed down) -- it never needs the
    // outer workspace page's dialog host, unlike "Add Document" below,
    // which does.
    function _unlinkDocument(linkId) {
        if (root._employeeId.length === 0 || !root.platformCatalog || !root.platformCatalog.adminWorkspace || !linkId) {
            return
        }
        root.platformCatalog.adminWorkspace.unlinkEmployeeDocument(root._employeeId, linkId)
        root._refreshDocumentsPage()
    }

    // User Account/Assignments/Timesheets/Certifications/Audit are not
    // tabs -- see Related Actions and Overview's System Access card for
    // the real relationships and optional cross-module navigation instead.
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Calendar" },
        { "label": "Documents", "count": root._documentsCatalog.filteredTotal || 0 },
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
            return "Working calendar and availability for this employee."
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
                { "id": "assign_calendar", "label": root._hasCalendarAssignment ? "Change Calendar" : "Assign Employee Override", "icon": "calendar", "enabled": root.canManageCalendar },
                { "id": "clear_calendar_assignment", "label": "Remove Override", "icon": "delete", "danger": true, "enabled": root._hasCalendarAssignment && root.canManageCalendar },
                { "id": "open_calendar_mgmt", "label": root._hasCalendarAssignment ? "Open Calendar" : "Open Calendar Management", "icon": "chevron_right" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        return []
    }
    readonly property bool _showSectionToolbar: root._activeSectionLabel === "Overview" || root._activeSectionLabel === "Calendar"

    readonly property var _employeeInformationFields: [
        { "label": "Employee Name", "value": root._displayValue(root._state.fullName || root.employee.title) },
        { "label": "Employee Number", "value": root._displayValue(root._employeeCode) }
    ]
    readonly property var _employmentFields: [
        { "label": "Job Title", "value": root._displayValue(root._jobTitle) },
        { "label": "Employment Type", "value": root._displayValue(String(root._state.employmentType || "").replace(/_/g, " ")) }
    ]
    readonly property var _organizationalAssignmentFields: [
        { "label": "Organization", "value": root._displayValue(root._state.organizationName) },
        { "label": "Department", "value": root._displayValue(root._departmentName) },
        { "label": "Site", "value": root._displayValue(root._state.siteName) }
    ]
    readonly property var _contactFields: [
        { "label": "Email", "value": root._displayValue(root._state.email) },
        { "label": "Phone", "value": root._displayValue(root._state.phone) }
    ]
    // Manage Calendar is a context-preserving local action (this employee's
    // own tab). Open User Account (when linked) is real cross-module
    // navigation to the Users workspace -- a PM "Open Resource" action is
    // deliberately not offered here: no approved Employee -> PM Resource
    // navigation target currently resolves, and inventing one would mean
    // either a fake link or a Platform -> PM import, both out of scope.
    readonly property var _relatedActions: {
        const actions = [
            { "id": "calendar", "label": "Manage Calendar", "icon": "calendar" }
        ]
        if (root.systemAccess.linked) {
            actions.push({ "id": "open_user_account", "label": "Open User Account", "icon": "chevron_right" })
        }
        return actions
    }

    function _navigateFromOverview(destinationId) {
        const label = destinationId === "calendar" ? "Calendar" : ""
        const index = label.length > 0 ? root._indexOfSection(label) : -1
        if (index >= 0) {
            detailPage.scrollToSection(index)
            return
        }
        root.actionRequested(destinationId)
    }

    onEmployeeChanged: {
        root._refreshActivityPage()
        root._refreshRecentActivity()
        root._refreshDocumentsPage()
    }
    Component.onCompleted: {
        root._refreshActivityPage()
        root._refreshRecentActivity()
        root._refreshDocumentsPage()
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
                loadingMessage: "Loading employee overview..."
                sourceComponent: Component {
                    EmployeeSections.EmployeeOverviewSection {
                        employeeInformationFields: root._employeeInformationFields
                        employmentFields: root._employmentFields
                        organizationalAssignmentFields: root._organizationalAssignmentFields
                        contactFields: root._contactFields
                        relatedActions: root._relatedActions
                        recentActivity: root._recentActivity
                        calendarSummary: root.empCalendarSummary
                        systemAccess: root.systemAccess
                        canManageSystemAccess: root.canManageSystemAccess

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
                        onLinkUserAccountRequested: root.actionRequested("link_user_account")
                        onUnlinkUserAccountRequested: root.actionRequested("unlink_user_account")
                        onOpenUserAccountRequested: root.actionRequested("open_user_account")
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
                loadingMessage: "Loading employee calendar..."
                sourceComponent: Component {
                    EmployeeSections.EmployeeCalendarSection {
                        entityId: root._employeeId
                        entityLabel: root._title
                        assignedCalendar: root.empCalendarAssignment
                        sourceChain: root.calendarSourceChain
                        effectiveCalendarSummary: root.empCalendarSummary
                        busy: root.busy
                        onAssignCalendarRequested: root.actionRequested("assign_calendar")
                        onOpenCalendarManagementRequested: root.actionRequested("open_calendar_mgmt")
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Documents"
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: documentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Documents"
                keepLoaded: true
                loadingMessage: "Loading employee documents..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    EmployeeSections.EmployeeDocumentsSection {
                        canWrite: root.canWrite
                        busy: root.busy
                        errorMessage: root.errorMessage
                        feedbackMessage: root.feedbackMessage
                        viewportHeight: Math.max(420, detailPage.contentViewportHeight)

                        catalog: root._documentsCatalog
                        columns: root._documentsColumns
                        searchText: root._documentsSearch
                        statusFilterOptions: root._documentsStatusFilterOptions
                        statusFilter: root._documentsStatusFilter
                        typeFilterOptions: root._documentsTypeFilterOptions
                        typeFilter: root._documentsTypeFilter

                        onAddDocumentRequested: root.actionRequested("add_document")
                        onRowActivated: function(documentId) { root.relatedRowActivated("documents", documentId) }
                        onUnlinkRequested: function(linkId) { root._unlinkDocument(linkId) }
                        onRefreshRequested: root._refreshDocumentsPage()
                        onSearchChanged: function(text) {
                            root._documentsSearch = text
                            root._documentsPage = 1
                            root._refreshDocumentsPage()
                        }
                        onPageRequested: function(page) {
                            root._documentsPage = page
                            root._refreshDocumentsPage()
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._documentsPageSize = pageSize
                            root._documentsPage = 1
                            root._refreshDocumentsPage()
                        }
                        onClearFiltersRequested: {
                            root._documentsSearch = ""
                            root._documentsStatusFilter = ""
                            root._documentsTypeFilter = ""
                            root._documentsPage = 1
                            root._refreshDocumentsPage()
                        }
                        onStatusFilterRequested: function(value) {
                            root._documentsStatusFilter = value
                            root._documentsPage = 1
                            root._refreshDocumentsPage()
                        }
                        onTypeFilterRequested: function(value) {
                            root._documentsTypeFilter = value
                            root._documentsPage = 1
                            root._refreshDocumentsPage()
                        }
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
                loadingMessage: "Loading employee activity..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    EmployeeSections.EmployeeActivitySection {
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
