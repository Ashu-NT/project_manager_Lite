pragma ComponentBehavior: Bound
import QtQuick

AdminEntityDetailPage {
    id: root

    property var party: ({})

    readonly property var _state: (root.party && root.party.state) ? root.party.state : ({})
    readonly property bool _isActive: root._state.isActive === true

    entity: root.party
    fallbackTitle: "Party"
    contextLabel: "Commercial Profile"
    contextSubtitle: "Shared supplier, customer, and partner master profile used across the platform."
    contextMessage: "Party records stay platform-owned. Downstream procurement, maintenance, and PM workflows should reference these master records rather than duplicating them."
    notesTitle: "Party Notes"
    notesMessage: String(root._state.notes || root.party.supportingText || "")
    overviewActions: [
        { "id": "edit", "label": "Edit", "icon": "edit" },
        { "id": "toggle_active", "label": root._isActive ? "Set Inactive" : "Set Active", "icon": "approve" },
        { "id": "refresh", "label": "Refresh", "icon": "refresh" }
    ]
    contextActions: [
        { "id": "refresh", "label": "Refresh", "icon": "refresh" }
    ]
    auditActions: [
        { "id": "show_audit", "label": "Open Audit", "icon": "chevron_right" }
    ]
    overviewFields: [
        { "label": "Party Code", "value": root._state.partyCode },
        { "label": "Party Name", "value": root._state.partyName || root.party.title },
        { "label": "Party Type", "value": root._state.partyType },
        { "label": "Legal Name", "value": root._state.legalName },
        { "label": "Status", "value": root.party.statusLabel },
        { "label": "Version", "value": root._state.version }
    ]
    contextFields: [
        { "label": "Contact", "value": root._state.contactName },
        { "label": "Email", "value": root._state.email },
        { "label": "Phone", "value": root._state.phone },
        { "label": "Location", "value": [root._state.city, root._state.country].filter(function(value) { return String(value || "").length > 0 }).join(", ") },
        { "label": "Website", "value": root._state.website },
        { "label": "Tax Registration", "value": root._state.taxRegistrationNumber }
    ]
}
