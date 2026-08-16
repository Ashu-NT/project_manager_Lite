pragma ComponentBehavior: Bound

import QtQuick
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers


Item {
    id: root

    // -- Destination model ------------------------------------------------
    // Stable string ids, not array indexes, since PlatformWorkspace needs a
    // durable key to drive its content host and (for tenants) gate
    // visibility on real entitlement state.
    property string selectedDestination: "overview"
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property bool collapsed: false

    signal destinationSelected(string destinationId)

    readonly property var _allDestinations: [
        { id: "overview", label: "Overview", icon: "dashboard", requiredPermissions: [] },
        { id: "organizations", label: "Organizations", group: "Organization", icon: "organization", requiredPermissions: ["settings.manage"] },
        { id: "sites", label: "Sites", group: "Organization", icon: "site", requiredPermissions: ["settings.manage", "site.read"] },
        { id: "departments", label: "Departments", group: "Organization", icon: "department", requiredPermissions: ["settings.manage", "department.read"] },
        { id: "employees", label: "Employees", group: "Organization", icon: "employee", requiredPermissions: ["employee.read"] },
        { id: "parties", label: "Parties", group: "Organization", icon: "party", requiredPermissions: ["settings.manage", "party.read"] },
        { id: "calendars", label: "Calendars", icon: "calendar", requiredPermissions: ["task.read"] },
        { id: "users", label: "Users", group: "Identity & Access", icon: "user", requiredPermissions: ["auth.manage", "auth.read", "access.manage", "security.manage"] },
        { id: "access", label: "Access", group: "Identity & Access", icon: "access", requiredPermissions: ["access.manage"] },
        { id: "documents", label: "Documents", group: "Documents", icon: "documents", requiredPermissions: ["settings.manage"] },
        { id: "structures", label: "Structures", group: "Documents", icon: "module", requiredPermissions: ["settings.manage"] },
        { id: "control_approvals", label: "Approvals", group: "Control", icon: "approve", requiredPermissions: ["approval.request", "approval.decide"] },
        { id: "control_audit", label: "Audit", group: "Control", icon: "audit", requiredPermissions: ["audit.read"] },
        { id: "settings", label: "Settings", icon: "settings", requiredPermissions: ["settings.manage"] },
        { id: "tenants", label: "Tenant Administration", icon: "tenant", requiredPermissions: ["platform.admin"] },
    ]

    function _isVisible(destination) {
        const required = destination.requiredPermissions || []
        if (required.length === 0) {
            return true
        }
        if (!root.platformCatalog) {
            // No catalog wired (QML preview/offscreen load) -- show
            // everything rather than an empty rail.
            return true
        }
        return root.platformCatalog.hasAnyPermission(required)
    }

    readonly property var _destinations: root._allDestinations.filter(function(destination) {
        return root._isVisible(destination)
    })

    readonly property int _selectedIndex: {
        const destinations = root._destinations
        for (let i = 0; i < destinations.length; i += 1) {
            if (destinations[i].id === root.selectedDestination) {
                return i
            }
        }
        return 0
    }

    implicitWidth: _rail.implicitWidth

    AppWidgets.GroupedNavigationRail {
        id: _rail
        anchors.fill: parent
        items: root._destinations
        activeIndex: root._selectedIndex
        collapsed: root.collapsed
        autoCollapseAtNarrowWidth: true
        groupsCollapsedByDefault: false
        showRailToggle: true
        railTitle: "Platform"

        onCollapsedChanged: root.collapsed = _rail.collapsed

        onItemActivated: function(index) {
            const destinations = root._destinations
            if (index >= 0 && index < destinations.length) {
                root.destinationSelected(destinations[index].id)
            }
        }
    }
}
