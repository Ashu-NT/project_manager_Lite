pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents
import control 1.0 as Control
import settings 1.0 as Settings
import tenants 1.0 as Tenants
import organization.organizations 1.0 as OrganizationsOrg
import organization.sites 1.0 as SitesOrg
import organization.departments 1.0 as DepartmentsOrg
import organization.employees 1.0 as EmployeesOrg
import organization.parties 1.0 as PartiesOrg
import calendars 1.0 as CalendarsOrg
import identity_access.users 1.0 as UsersOrg
import identity_access.access 1.0 as AccessOrg
import documents 1.0 as DocumentsOrg


Item {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog

    // -- Canonical destination state --------------------------------
    property string activeDestination: "overview"

    readonly property bool _isMultiTenant: root.platformCatalog
        ? root.platformCatalog.tenantSwitcher.isMultiTenant
        : false

    // R4/R5: every Platform capability (Organizations/Sites/Departments/
    // Employees/Parties/Calendars in R4; Users/Access/Documents/Structures
    // in R5) is its own standalone page, hosted here as a persistent
    // sibling gated purely by destination id -- the Admin Console facade
    // that used to compose these has been fully retired (R5.9).
    readonly property var _directSurfaceDestinations: [
        "organizations", "sites", "departments", "employees", "parties", "calendars",
        "users", "access", "documents", "structures"
    ]

    readonly property string _activeSurface: {
        if (root.activeDestination === "control_approvals" || root.activeDestination === "control_audit") {
            return "control"
        }
        if (root.activeDestination === "settings") {
            return "settings"
        }
        if (root.activeDestination === "tenants") {
            return "tenants"
        }
        if (root._directSurfaceDestinations.indexOf(root.activeDestination) >= 0) {
            return root.activeDestination
        }
        return "overview"
    }

    // R4.7: cross-entity "jump to related record" navigation. Sites' and
    // Departments' detail pages already surface related-record rows
    // (departments/employees); this bubbles those clicks to a destination
    // switch plus opening the specific row on the target page, which stays
    // instantiated (persistent sibling) so its own state survives the jump.
    function _onRelatedRecordRequested(destinationId, rowId) {
        root.activeDestination = destinationId
        if (destinationId === "organizations") _organizationsPage.openRecord(rowId)
        else if (destinationId === "sites") _sitesPage.openRecord(rowId)
        else if (destinationId === "departments") _departmentsPage.openRecord(rowId)
        else if (destinationId === "employees") _employeesPage.openRecord(rowId)
        else if (destinationId === "parties") _partiesPage.openRecord(rowId)
        else if (destinationId === "calendars") _calendarsPage.openRecord(rowId)
    }

    // -- Active organization (for ContextBar) ------------------------
    // Reuses the same "find the row with state.isActive" pattern
    // AdminDialogHost.qml's _activeOrganizationName() already uses in
    // production -- no new backend state invented for this.
    readonly property var _organizationItems: root.platformCatalog
        ? ((root.platformCatalog.adminWorkspace.organizations || {}).items || [])
        : []

    readonly property string _activeOrganizationName: {
        for (let i = 0; i < root._organizationItems.length; i += 1) {
            const item = root._organizationItems[i] || {}
            const state = item.state || {}
            if (state.isActive === true) {
                return String(state.displayName || item.title || "")
            }
        }
        return ""
    }

    readonly property var _organizationOptions: {
        const options = []
        for (let i = 0; i < root._organizationItems.length; i += 1) {
            const item = root._organizationItems[i] || {}
            const state = item.state || {}
            const id = String(state.organizationId || state.id || item.id || "")
            if (id.length === 0) {
                continue
            }
            options.push({ "id": id, "label": String(state.displayName || item.title || id) })
        }
        return options
    }

    // Tenant items are a FLAT QVariantList of flat dicts
    // ({id, displayName, tenantCode, tenantStatus, isActive}) -- unlike the
    // {items:[{..., state:{...}}]} shape used by the other catalogs, per
    // TenantSwitcherController._load_tenants(). Mirrors the lookup pattern
    // already used in production by TenantSwitcher.qml's `_activeName`.
    readonly property var _tenantItems: root.platformCatalog
        ? (root.platformCatalog.tenantSwitcher.tenants || [])
        : []

    readonly property string _activeTenantName: {
        if (!root.platformCatalog) {
            return ""
        }
        const activeId = root.platformCatalog.tenantSwitcher.activeTenantId
        for (let i = 0; i < root._tenantItems.length; i += 1) {
            const item = root._tenantItems[i] || {}
            if (item.id === activeId) {
                return String(item.displayName || item.tenantCode || "")
            }
        }
        return ""
    }

    readonly property var _tenantOptions: {
        const options = []
        for (let i = 0; i < root._tenantItems.length; i += 1) {
            const item = root._tenantItems[i] || {}
            const id = String(item.id || "")
            if (id.length === 0) {
                continue
            }
            options.push({ "id": id, "label": String(item.displayName || item.tenantCode || id) })
        }
        return options
    }

    // -- Overview (R3) -------------------------------------------------
    // All figures below are read directly from already-backed, already-
    // refreshed controller state (admin_presenter.build_overview() and
    // Control's approval queue) -- no new backend, no invented metrics.
    // Department/Site breakdowns are explicitly out of scope (design doc
    // §6/§25 -- not backed today, tracked as separate backlog).
    readonly property var _overview: root.platformCatalog
        ? (root.platformCatalog.adminWorkspace.overview || {})
        : {}

    readonly property var _overviewMetrics: root._overview.metrics || []

    // Metric label -> Platform destination id, for click-to-navigate.
    readonly property var _metricDestinationByLabel: ({
        "Organizations": "organizations",
        "Sites": "sites",
        "Departments": "departments",
        "Employees": "employees",
        "Users": "users",
        "Documents": "documents"
    })

    readonly property int _pendingApprovalsCount: root.platformCatalog
        ? (root.platformCatalog.controlWorkspace.approvalQueue.items || []).length
        : 0

    readonly property var _overviewHighlightCards: [
        {
            "title": "Pending Approvals",
            "rows": [
                { "label": "Open", "value": String(root._pendingApprovalsCount), "supportingText": "Awaiting review" }
            ]
        }
    ]

    // Doc §6: "Overview would show a trimmed, most-recent slice of the same
    // feed, not a new data source" -- the raw feed can return up to 50
    // entries; Overview shows only the most recent handful.
    readonly property var _overviewActivityItems: (root._overview.activityFeed || []).slice(0, 6)

    // Employees/Sites-by-department/site breakdowns are explicitly not
    // backed today (design doc §6/§25 -- backlog, not part of this
    // redesign). Shown as labeled placeholder cards rather than silently
    // omitted or faked.
    readonly property var _overviewUnavailableBreakdowns: [
        { "title": "Employees by Department", "message": "Not yet available — requires new backend rollup work, tracked as backlog." },
        { "title": "Employees by Site", "message": "Not yet available — requires new backend rollup work, tracked as backlog." }
    ]

    function _onOverviewMetricActivated(index) {
        const metrics = root._overviewMetrics
        if (index < 0 || index >= metrics.length) {
            return
        }
        const label = String(metrics[index].label || "")
        const destination = root._metricDestinationByLabel[label]
        if (destination) {
            root.activeDestination = destination
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppWidgets.ContextBar {
            Layout.fillWidth: true
            tenantSwitcherVisible: root._isMultiTenant
            tenantName: root._activeTenantName
            tenantOptions: root._tenantOptions
            organizationName: root._activeOrganizationName
            organizationOptions: root._organizationOptions

            onTenantSelected: function(tenantId) {
                if (root.platformCatalog) {
                    root.platformCatalog.tenantSwitcher.switchToTenant(tenantId)
                }
            }
            onOrganizationSelected: function(organizationId) {
                if (root.platformCatalog) {
                    root.platformCatalog.adminWorkspace.setActiveOrganization(organizationId)
                }
            }
            onManageTenantsRequested: root.activeDestination = "tenants"
            onManageOrganizationsRequested: root.activeDestination = "organizations"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            PlatformComponents.PlatformNavigation {
                Layout.fillHeight: true
                selectedDestination: root.activeDestination
                onDestinationSelected: function(destinationId) {
                    root.activeDestination = destinationId
                }
            }

            Rectangle {
                Layout.preferredWidth: Theme.AppTheme.borderWidthThin
                Layout.fillHeight: true
                color: Theme.AppTheme.divider
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                AppLayouts.WorkspaceOverviewPage {
                    anchors.fill: parent
                    visible: root._activeSurface === "overview"
                    title: "Platform Overview"
                    subtitle: String(root._overview.subtitle || "")
                    metrics: root._overviewMetrics
                    metricsClickable: true
                    onMetricActivated: function(index) { root._onOverviewMetricActivated(index) }
                    highlightCards: root._overviewHighlightCards
                    activityItems: root._overviewActivityItems
                    activityEmptyText: "No recent activity"
                    unavailableBreakdowns: root._overviewUnavailableBreakdowns
                }

                UsersOrg.UsersWorkspacePage {
                    id: _usersPage
                    anchors.fill: parent
                    visible: root._activeSurface === "users"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                AccessOrg.AccessWorkspacePage {
                    id: _accessPage
                    anchors.fill: parent
                    visible: root._activeSurface === "access"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                DocumentsOrg.DocumentsWorkspacePage {
                    id: _documentsPage
                    anchors.fill: parent
                    visible: root._activeSurface === "documents"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                DocumentsOrg.DocumentStructuresWorkspacePage {
                    id: _structuresPage
                    anchors.fill: parent
                    visible: root._activeSurface === "structures"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                OrganizationsOrg.OrganizationsWorkspacePage {
                    id: _organizationsPage
                    anchors.fill: parent
                    visible: root._activeSurface === "organizations"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                SitesOrg.SitesWorkspacePage {
                    id: _sitesPage
                    anchors.fill: parent
                    visible: root._activeSurface === "sites"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                    onRelatedRecordRequested: function(destinationId, rowId) {
                        root._onRelatedRecordRequested(destinationId, rowId)
                    }
                }

                DepartmentsOrg.DepartmentsWorkspacePage {
                    id: _departmentsPage
                    anchors.fill: parent
                    visible: root._activeSurface === "departments"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                    onRelatedRecordRequested: function(destinationId, rowId) {
                        root._onRelatedRecordRequested(destinationId, rowId)
                    }
                }

                EmployeesOrg.EmployeesWorkspacePage {
                    id: _employeesPage
                    anchors.fill: parent
                    visible: root._activeSurface === "employees"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                PartiesOrg.PartiesWorkspacePage {
                    id: _partiesPage
                    anchors.fill: parent
                    visible: root._activeSurface === "parties"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                CalendarsOrg.CalendarsWorkspacePage {
                    id: _calendarsPage
                    anchors.fill: parent
                    visible: root._activeSurface === "calendars"
                    platformCatalog: root.platformCatalog
                    onNavigateToDestination: function(destinationId) { root.activeDestination = destinationId }
                }

                Control.ControlWorkspacePage {
                    anchors.fill: parent
                    visible: root._activeSurface === "control"
                    platformCatalog: root.platformCatalog
                    activePanel: root.activeDestination === "control_audit" ? "audit" : "approvals"
                }

                Settings.SettingsWorkspacePage {
                    anchors.fill: parent
                    visible: root._activeSurface === "settings"
                    platformCatalog: root.platformCatalog
                }

                Tenants.TenantManagementWorkspacePage {
                    anchors.fill: parent
                    visible: root._activeSurface === "tenants"
                    platformCatalog: root.platformCatalog
                }
            }
        }
    }
}
