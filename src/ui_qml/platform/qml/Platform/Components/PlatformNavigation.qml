pragma ComponentBehavior: Bound

import QtQuick
import App.Widgets 1.0 as AppWidgets

// The Platform-level navigation specialization. Owns the
// approved target destination taxonomy, grouping, and selection semantics.
// Composed from the shared GroupedNavigationRail primitive -- this file is
// the ONLY place Platform-specific destination knowledge lives; the
// primitive itself stays business-agnostic. Sibling of SectionNavigationRail
// under the same primitive, not a replacement of it.
Item {
    id: root

    // -- Destination model ------------------------------------------------
    // Stable string ids, not array indexes, since PlatformWorkspace needs a
    // durable key to drive its content host and (for tenants) gate
    // visibility on real entitlement state.
    property string selectedDestination: "overview"
    property bool tenantAdministrationVisible: true
    property bool collapsed: false

    signal destinationSelected(string destinationId)

    readonly property var _destinations: {
        const list = [
            { id: "overview", label: "Overview", icon: "dashboard" },
            { id: "organizations", label: "Organizations", group: "Organization", icon: "organization" },
            { id: "sites", label: "Sites", group: "Organization", icon: "site" },
            { id: "departments", label: "Departments", group: "Organization", icon: "department" },
            { id: "employees", label: "Employees", group: "Organization", icon: "employee" },
            { id: "parties", label: "Parties", group: "Organization", icon: "party" },
            { id: "calendars", label: "Calendars", icon: "calendar" },
            { id: "users", label: "Users", group: "Identity & Access", icon: "user" },
            { id: "access", label: "Access", group: "Identity & Access", icon: "access" },
            { id: "documents", label: "Documents", group: "Documents", icon: "documents" },
            { id: "structures", label: "Structures", group: "Documents", icon: "module" },
            { id: "control_approvals", label: "Approvals", group: "Control", icon: "approve" },
            { id: "control_audit", label: "Audit", group: "Control", icon: "audit" },
            { id: "settings", label: "Settings", icon: "settings" },
            { id: "support", label: "Support", icon: "support" },
        ]
        if (root.tenantAdministrationVisible) {
            list.push({ id: "tenants", label: "Tenant Administration", icon: "tenant" })
        }
        return list
    }

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
