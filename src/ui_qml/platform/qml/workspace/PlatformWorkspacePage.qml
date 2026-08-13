pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents
import admin_console 1.0 as AdminConsole
import control 1.0 as Control
import settings 1.0 as Settings
import tenants 1.0 as Tenants

// The unified Platform workspace shell (R2):
//
//   PlatformWorkspace
//   |-- PlatformNavigation
//   |-- ContextBar
//   `-- content host (the existing 4 pages, hosted persistently)
//
// This is the single canonical source of truth for the selected Platform
// destination (`activeDestination`); PlatformNavigation's selection and the
// content host's visible page both derive from it, rather than each holding
// independent state that has to stay in sync.
//
// R2 does not redesign any capability's internals: AdminConsolePage.qml,
// ControlWorkspacePage.qml, SettingsWorkspacePage.qml, and
// TenantManagementWorkspacePage.qml are hosted here exactly as they exist
// today, minus their own now-redundant top-level navigation where one
// existed (AdminConsolePage's internal AdminNavSidebar -- see its
// `externallyNavigated` property).
Item {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog

    // -- Canonical destination state --------------------------------
    property string activeDestination: "overview"

    readonly property bool _isMultiTenant: root.platformCatalog
        ? root.platformCatalog.tenantSwitcher.isMultiTenant
        : false

    // Destinations hosted by the existing Admin Console page (unchanged
    // content, only which section is externally selected changes).
    readonly property var _adminSurfaceDestinations: [
        "organizations", "sites", "departments", "employees", "parties",
        "calendars", "users", "access", "documents", "structures", "support"
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
        if (root._adminSurfaceDestinations.indexOf(root.activeDestination) >= 0) {
            return "admin"
        }
        return "overview"
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
                tenantAdministrationVisible: root._isMultiTenant
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

                AppWidgets.EmptyState {
                    anchors.fill: parent
                    visible: root._activeSurface === "overview"
                    title: "Platform Overview"
                    message: "The full Overview dashboard is implemented in a later phase (R3). This destination is a structural placeholder only."
                }

                AdminConsole.AdminConsolePage {
                    anchors.fill: parent
                    visible: root._activeSurface === "admin"
                    platformCatalog: root.platformCatalog
                    externallyNavigated: true
                    activeSection: root._adminSurfaceDestinations.indexOf(root.activeDestination) >= 0
                        ? root.activeDestination
                        : "organizations"
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
