pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Shell.Context 1.0 as ShellContexts
import workspaces.control 1.0 as Control
import workspaces.settings 1.0 as Settings
import workspaces.tenant_management 1.0 as Tenants
import workspaces.organizations 1.0 as OrganizationsOrg
import workspaces.sites 1.0 as SitesOrg
import workspaces.departments 1.0 as DepartmentsOrg
import workspaces.employees 1.0 as EmployeesOrg
import workspaces.parties 1.0 as PartiesOrg
import workspaces.calendars 1.0 as CalendarsOrg
import workspaces.users 1.0 as UsersOrg
import workspaces.access 1.0 as AccessOrg
import workspaces.documents 1.0 as DocumentsOrg
import workspaces.overview 1.0 as Overview


Item {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ShellContexts.ShellContext shellModel
    property var breadcrumb: []

    // -- Canonical destination state --------------------------------
    // Destination selection is owned by platformCatalog (so it can be
    // driven from the shell's Context Navigation Tree too, not only from
    // this page's own internal nav); this page renders whichever
    // destination is currently selected there.
    readonly property string activeDestination: root.platformCatalog
        ? root.platformCatalog.currentDestinationId
        : "overview"

    function _selectDestination(destinationId) {
        if (root.platformCatalog) {
            root.platformCatalog.selectDestination(destinationId)
        }
    }

    // Each surface's Item is created only the first time it becomes active
    // (Loader.active flips true and stays true), then stays instantiated
    // for the rest of the session -- only one surface is ever `visible` at a time.
    property var _activatedSurfaces: ({})

    function _markSurfaceLoaded(surfaceKey) {
        if (root._activatedSurfaces[surfaceKey] === true) {
            return
        }
        const updated = Object.assign({}, root._activatedSurfaces)
        updated[surfaceKey] = true
        root._activatedSurfaces = updated
    }

    onActiveDestinationChanged: {
        root._ensureWorkspaceLoaded(root.activeDestination)
        root._markSurfaceLoaded(root._surfaceFor(root.activeDestination))
    }
    Component.onCompleted: {
        root._ensureWorkspaceLoaded(root.activeDestination)
        root._markSurfaceLoaded(root._surfaceFor(root.activeDestination))
    }

    function _ensureWorkspaceLoaded(destinationId) {
        if (!root.platformCatalog) {
            return
        }
        if (destinationId === "access") {
            root.platformCatalog.adminAccessWorkspace.ensureLoaded()
            return
        }
        if (destinationId === "control_approvals" || destinationId === "control_audit") {
            root.platformCatalog.controlWorkspace.ensureLoaded()
            return
        }
        if (destinationId === "settings") {
            root.platformCatalog.settingsWorkspace.ensureLoaded()
            return
        }
    }

    readonly property bool _isMultiTenant: root.platformCatalog
        ? root.platformCatalog.tenantSwitcher.isMultiTenant
        : false

    readonly property var _directSurfaceDestinations: [
        "organizations", "sites", "departments", "employees", "parties", "calendars",
        "users", "access", "documents", "structures"
    ]

    function _surfaceFor(destinationId) {
        if (destinationId === "control_approvals" || destinationId === "control_audit") {
            return "control"
        }
        if (destinationId === "settings") {
            return "settings"
        }
        if (destinationId === "tenants") {
            return "tenants"
        }
        if (root._directSurfaceDestinations.indexOf(destinationId) >= 0) {
            return destinationId
        }
        return "overview"
    }

    readonly property string _activeSurface: root._surfaceFor(root.activeDestination)


    function _onRelatedRecordRequested(destinationId, rowId) {
        root._selectDestination(destinationId)
        if (destinationId === "organizations") _organizationsLoader.item.openRecord(rowId)
        else if (destinationId === "sites") _sitesLoader.item.openRecord(rowId)
        else if (destinationId === "departments") _departmentsLoader.item.openRecord(rowId)
        else if (destinationId === "employees") _employeesLoader.item.openRecord(rowId)
        else if (destinationId === "parties") _partiesLoader.item.openRecord(rowId)
        else if (destinationId === "calendars") _calendarsLoader.item.openRecord(rowId)
    }

    // -- Active organization (for ContextBar) ------------------------
    readonly property var _organizationItems: root.platformCatalog
        ? (root.platformCatalog.organizationSwitcher.organizations || [])
        : []

    readonly property string _activeOrganizationName: {
        if (!root.platformCatalog) {
            return ""
        }
        const activeId = root.platformCatalog.organizationSwitcher.activeOrganizationId
        for (let i = 0; i < root._organizationItems.length; i += 1) {
            const item = root._organizationItems[i] || {}
            if (item.id === activeId) {
                return String(item.displayName || item.organizationCode || "")
            }
        }
        return ""
    }

    readonly property var _organizationOptions: {
        const options = []
        for (let i = 0; i < root._organizationItems.length; i += 1) {
            const item = root._organizationItems[i] || {}
            const id = String(item.id || "")
            if (id.length === 0) {
                continue
            }
            options.push({ "id": id, "label": String(item.displayName || id) })
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

    // -- Overview -------------------------------------------------
    // All figures below are read directly from already-backed, already-
    // refreshed controller state (admin_presenter.build_overview(), which
    // itself composes the runtime, master-data, approval, audit, and
    // tenant desktop APIs) -- no new backend, no invented metrics.
    readonly property var _overview: root.platformCatalog
        ? (root.platformCatalog.adminWorkspace.overview || {})
        : {}

    readonly property var _overviewMetrics: {
        const metrics = root._overview.metrics || []
        const enriched = []
        for (let i = 0; i < metrics.length; i += 1) {
            const metric = metrics[i]
            const destination = root._destinationByLabel[String(metric.label || "")]
            enriched.push(Object.assign({}, metric, {
                "clickable": !!destination && root._isDestinationAccessible(destination)
            }))
        }
        return enriched
    }

    // Metric/row label -> Platform destination id, for click-to-navigate.
    readonly property var _destinationByLabel: ({
        "Organizations": "organizations",
        "Sites": "sites",
        "Departments": "departments",
        "Employees": "employees",
        "Parties": "parties",
        "Users": "users",
        "Pending approvals": "control_approvals",
        "Documents": "documents",
        "Document Structures": "structures"
    })

    // A destination is only ever offered as a click target when it is
    // actually present in the already-permission-filtered Context
    // Navigation Tree -- the same accessibility source the sidebar itself
    // uses, never a raw permission code re-derived in QML.
    function _isDestinationAccessible(destinationId) {
        const groups = (root.platformCatalog && root.platformCatalog.contextNavigation) || []
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

    function _navigateByLabel(label) {
        const destination = root._destinationByLabel[label]
        if (destination && root._isDestinationAccessible(destination)) {
            root._selectDestination(destination)
        }
    }

    function _overviewSectionByTitle(title) {
        const sections = root._overview.sections || []
        for (let i = 0; i < sections.length; i += 1) {
            if (sections[i].title === title) {
                return sections[i]
            }
        }
        return null
    }

    readonly property var _organizationSnapshot: {
        const section = root._overviewSectionByTitle("Organization Snapshot")
        if (!section) {
            return {}
        }
        const rows = section.rows || []
        const enriched = []
        for (let i = 0; i < rows.length; i += 1) {
            const row = rows[i]
            const destination = root._destinationByLabel[String(row.label || "")]
            enriched.push(Object.assign({}, row, {
                "clickable": !!destination && root._isDestinationAccessible(destination)
            }))
        }
        return Object.assign({}, section, { "rows": enriched })
    }
    readonly property var _accessSecurity: root._overviewSectionByTitle("Access & Security") || {}
    readonly property var _moduleTenantStatus: root._overviewSectionByTitle("Module & Tenant Status") || {}

    // "Documents at a glance" -- real SQL-backed totals from
    // admin_overview_presenter.py, replacing the earlier ad-hoc Employees-
    // by-Department/Site breakdown (still available from the presenter's
    // own dependencies; simply not surfaced on Overview any more, since the
    // approved reference composition has no room for a fourth summary
    // section here).
    readonly property var _documentsGlance: {
        const cards = root._overview.breakdownCards || []
        const card = cards.length > 0 ? cards[0] : {}
        const metrics = card.metrics || []
        const enriched = []
        for (let i = 0; i < metrics.length; i += 1) {
            const metric = metrics[i]
            const destination = root._destinationByLabel[String(metric.label || "")]
            enriched.push(Object.assign({}, metric, {
                "clickable": !!destination && root._isDestinationAccessible(destination)
            }))
        }
        return Object.assign({}, card, { "metrics": enriched })
    }

    readonly property var _recentActivity: root._overview.recentActivity || []
    readonly property var _approvalActions: root._overview.approvalActions || {}

    function _onOverviewMetricActivated(index) {
        const metrics = root._overviewMetrics
        if (index < 0 || index >= metrics.length) {
            return
        }
        root._navigateByLabel(String(metrics[index].label || ""))
    }

    function _onOrganizationRowActivated(index) {
        const rows = root._organizationSnapshot.rows || []
        if (index < 0 || index >= rows.length) {
            return
        }
        root._navigateByLabel(String(rows[index].label || ""))
    }

    function _onApprovalActionActivated(index) {
        const items = root._approvalActions.items || []
        if (index < 0 || index >= items.length) {
            return
        }
        if (root._isDestinationAccessible("control_approvals")) {
            root._selectDestination("control_approvals")
        }
    }

    function _onRecentActivityViewAllRequested() {
        if (root._isDestinationAccessible("control_audit")) {
            root._selectDestination("control_audit")
        }
    }

    function _onApprovalActionsViewAllRequested() {
        if (root._isDestinationAccessible("control_approvals")) {
            root._selectDestination("control_approvals")
        }
    }

    function _onDocumentsMetricActivated(index) {
        const metrics = root._documentsGlance.metrics || []
        if (index < 0 || index >= metrics.length) {
            return
        }
        root._navigateByLabel(String(metrics[index].label || ""))
    }

    function _onViewDocumentsRequested() {
        root._navigateByLabel("Documents")
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
                    root.platformCatalog.refreshCurrentPermissions()
                }
            }
            onOrganizationSelected: function(organizationId) {
                if (root.platformCatalog) {
                    root.platformCatalog.organizationSwitcher.switchToOrganization(organizationId)
                    root.platformCatalog.refreshCurrentPermissions()
                }
            }
            onManageTenantsRequested: root._selectDestination("tenants")
            onManageOrganizationsRequested: root._selectDestination("organizations")
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Loader {
                    id: _overviewLoader
                    objectName: "overviewLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["overview"] === true
                    visible: active && root._activeSurface === "overview"
                    asynchronous: false
                    sourceComponent: Component {
                        Overview.PlatformOverviewPage {
                            breadcrumb: root.breadcrumb
                            subtitle: String(root._overview.subtitle || "")
                            isLoading: root.platformCatalog ? root.platformCatalog.adminWorkspace.isLoading : false
                            errorMessage: root.platformCatalog ? root.platformCatalog.adminWorkspace.errorMessage : ""
                            emptyState: root.platformCatalog ? root.platformCatalog.adminWorkspace.emptyState : ""
                            metrics: root._overviewMetrics
                            onMetricActivated: function(index) { root._onOverviewMetricActivated(index) }
                            organizationSnapshot: root._organizationSnapshot
                            onOrganizationRowActivated: function(index) { root._onOrganizationRowActivated(index) }
                            accessSecurity: root._accessSecurity
                            moduleTenantStatus: root._moduleTenantStatus
                            recentActivity: root._recentActivity
                            recentActivityViewAllAccessible: root._isDestinationAccessible("control_audit")
                            onRecentActivityViewAllRequested: root._onRecentActivityViewAllRequested()
                            approvalActions: root._approvalActions
                            approvalActionsViewAllAccessible: root._isDestinationAccessible("control_approvals")
                            onApprovalActionsViewAllRequested: root._onApprovalActionsViewAllRequested()
                            onApprovalActionActivated: function(index) { root._onApprovalActionActivated(index) }
                            documentsGlance: root._documentsGlance
                            viewDocumentsAccessible: root._isDestinationAccessible("documents")
                            onViewDocumentsRequested: root._onViewDocumentsRequested()
                            onDocumentsMetricActivated: function(index) { root._onDocumentsMetricActivated(index) }
                        }
                    }
                }

                Loader {
                    id: _usersLoader
                    objectName: "usersLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["users"] === true
                    visible: active && root._activeSurface === "users"
                    asynchronous: false
                    sourceComponent: Component {
                        UsersOrg.UsersWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _accessLoader
                    objectName: "accessLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["access"] === true
                    visible: active && root._activeSurface === "access"
                    asynchronous: false
                    sourceComponent: Component {
                        AccessOrg.AccessWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _documentsLoader
                    objectName: "documentsLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["documents"] === true
                    visible: active && root._activeSurface === "documents"
                    asynchronous: false
                    sourceComponent: Component {
                        DocumentsOrg.DocumentsWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _structuresLoader
                    objectName: "structuresLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["structures"] === true
                    visible: active && root._activeSurface === "structures"
                    asynchronous: false
                    sourceComponent: Component {
                        DocumentsOrg.DocumentStructuresWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _organizationsLoader
                    objectName: "organizationsLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["organizations"] === true
                    visible: active && root._activeSurface === "organizations"
                    asynchronous: false
                    sourceComponent: Component {
                        OrganizationsOrg.OrganizationsWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _sitesLoader
                    objectName: "sitesLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["sites"] === true
                    visible: active && root._activeSurface === "sites"
                    asynchronous: false
                    sourceComponent: Component {
                        SitesOrg.SitesWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                            onRelatedRecordRequested: function(destinationId, rowId) {
                                root._onRelatedRecordRequested(destinationId, rowId)
                            }
                        }
                    }
                }

                Loader {
                    id: _departmentsLoader
                    objectName: "departmentsLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["departments"] === true
                    visible: active && root._activeSurface === "departments"
                    asynchronous: false
                    sourceComponent: Component {
                        DepartmentsOrg.DepartmentsWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                            onRelatedRecordRequested: function(destinationId, rowId) {
                                root._onRelatedRecordRequested(destinationId, rowId)
                            }
                        }
                    }
                }

                Loader {
                    id: _employeesLoader
                    objectName: "employeesLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["employees"] === true
                    visible: active && root._activeSurface === "employees"
                    asynchronous: false
                    sourceComponent: Component {
                        EmployeesOrg.EmployeesWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _partiesLoader
                    objectName: "partiesLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["parties"] === true
                    visible: active && root._activeSurface === "parties"
                    asynchronous: false
                    sourceComponent: Component {
                        PartiesOrg.PartiesWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _calendarsLoader
                    objectName: "calendarsLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["calendars"] === true
                    visible: active && root._activeSurface === "calendars"
                    asynchronous: false
                    sourceComponent: Component {
                        CalendarsOrg.CalendarsWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            onNavigateToDestination: function(destinationId) { root._selectDestination(destinationId) }
                        }
                    }
                }

                Loader {
                    id: _controlLoader
                    objectName: "controlLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["control"] === true
                    visible: active && root._activeSurface === "control"
                    asynchronous: false
                    sourceComponent: Component {
                        Control.ControlWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            activePanel: root.activeDestination === "control_audit" ? "audit" : "approvals"
                        }
                    }
                }

                Loader {
                    id: _settingsLoader
                    objectName: "settingsLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["settings"] === true
                    visible: active && root._activeSurface === "settings"
                    asynchronous: false
                    sourceComponent: Component {
                        Settings.SettingsWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                            shellModel: root.shellModel
                        }
                    }
                }

                Loader {
                    id: _tenantsLoader
                    objectName: "tenantsLoader"
                    anchors.fill: parent
                    active: root._activatedSurfaces["tenants"] === true
                    visible: active && root._activeSurface === "tenants"
                    asynchronous: false
                    sourceComponent: Component {
                        Tenants.TenantManagementWorkspacePage {
                            platformCatalog: root.platformCatalog
                            breadcrumb: root.breadcrumb
                        }
                    }
                }
            }
        }
    }
}
