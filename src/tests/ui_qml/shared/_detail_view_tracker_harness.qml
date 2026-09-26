pragma ComponentBehavior: Bound

import QtQuick
import App.Widgets 1.0 as AppWidgets
import workspaces.organizations 1.0 as OrganizationsWorkspace

// Test-only harness: exposes DetailViewTracker's counter directly, and
// toggles two independent Loaders that each create/destroy a real
// SectionDetailPage-based page (AdminOrganizationDetailPage) exactly the
// way every workspace page's own "detailOpen" Loader does -- proving the
// tracker increments on creation and decrements on destruction, and that
// it correctly reflects TWO simultaneously-open detail views (e.g.
// Organization Detail's own nested Site Detail) within one engine, without
// needing to drive a full shell + simulated row click.
Item {
    id: root

    property var _harnessOrganization: ({
        "id": "org-1",
        "title": "Harness Org",
        "statusLabel": {"label": "Active", "tone": "success"},
        "subtitle": "HARNESS | UTC",
        "state": {"organizationId": "org-1", "organizationCode": "HARNESS", "status": "active"}
    })

    property bool detailOpen: false
    property bool nestedDetailOpen: false
    readonly property int trackerOpenCount: AppWidgets.DetailViewTracker.openCount
    readonly property bool trackerAnyOpen: AppWidgets.DetailViewTracker.anyOpen

    Loader {
        active: root.detailOpen
        sourceComponent: Component {
            OrganizationsWorkspace.AdminOrganizationDetailPage {
                organization: root._harnessOrganization
            }
        }
    }

    Loader {
        active: root.nestedDetailOpen
        sourceComponent: Component {
            OrganizationsWorkspace.AdminOrganizationDetailPage {
                organization: root._harnessOrganization
            }
        }
    }
}
