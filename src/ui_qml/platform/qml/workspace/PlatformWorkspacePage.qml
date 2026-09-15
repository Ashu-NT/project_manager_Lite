pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Shell.Context 1.0 as ShellContexts
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
import workspace.overview 1.0 as Overview


Item {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ShellContexts.ShellContext shellModel

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
    // refreshed controller state (admin_presenter.build_overview() and
    // Control's approval queue) -- no new backend, no invented metrics.
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

    // Sections were already computed by admin_overview_presenter.py (real
    // SQL-backed totals) but had no QML consumer before this redesign --
    // surfaced here as extra highlight cards rather than left unused.
    function _overviewSectionByTitle(title) {
        const sections = root._overview.sections || []
        for (let i = 0; i < sections.length; i += 1) {
            if (sections[i].title === title) {
                return sections[i]
            }
        }
        return null
    }

    readonly property var _overviewHighlightCards: {
        const cards = [
            {
                "title": "Pending Approvals",
                "rows": [
                    { "label": "Open", "value": String(root._pendingApprovalsCount), "supportingText": "Awaiting review" }
                ]
            }
        ]
        const identitySection = root._overviewSectionByTitle("Identity And Workforce")
        if (identitySection) {
            cards.push({
                "title": identitySection.title,
                "rows": identitySection.rows,
                "emptyState": identitySection.emptyState
            })
        }
        const masterDataSection = root._overviewSectionByTitle("Master Data Coverage")
        if (masterDataSection) {
            cards.push({
                "title": masterDataSection.title,
                "rows": masterDataSection.rows,
                "emptyState": masterDataSection.emptyState
            })
        }
        return cards
    }

    // Employees by Department/Site: real SQL-backed breakdown cards from
    // admin_overview_presenter.py (EmployeeHeadcountReader.get_department_
    // breakdown/get_site_breakdown), no longer a hardcoded placeholder.
    readonly property var _overviewBreakdownCards: root._overview.breakdownCards || []

    function _onOverviewMetricActivated(index) {
        const metrics = root._overviewMetrics
        if (index < 0 || index >= metrics.length) {
            return
        }
        const label = String(metrics[index].label || "")
        const destination = root._metricDestinationByLabel[label]
        if (destination) {
            root._selectDestination(destination)
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
                            subtitle: String(root._overview.subtitle || "")
                            metrics: root._overviewMetrics
                            metricsClickable: true
                            onMetricActivated: function(index) { root._onOverviewMetricActivated(index) }
                            highlightCards: root._overviewHighlightCards
                            breakdownCards: root._overviewBreakdownCards
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
                        }
                    }
                }
            }
        }
    }
}
