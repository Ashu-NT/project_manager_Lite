pragma ComponentBehavior: Bound
import QtQuick

AdminEntityDetailPage {
    id: root

    property var structure: ({})

    readonly property var _state: (root.structure && root.structure.state) ? root.structure.state : ({})
    readonly property bool _isActive: root._state.isActive === true

    entity: root.structure
    fallbackTitle: "Document Structure"
    contextLabel: "Classification Context"
    contextSubtitle: "Document classification, scope, hierarchy, and default type behavior."
    contextMessage: "Document structures define shared governance for document catalogs. Document workspaces should reference these structures by ID and scope."
    notesTitle: "Structure Notes"
    notesMessage: String(root._state.description || root._state.notes || root.structure.supportingText || "")
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
        { "label": "Structure Code", "value": root._state.structureCode },
        { "label": "Display Name", "value": root._state.name || root.structure.title },
        { "label": "Object Scope", "value": root._state.objectScope },
        { "label": "Default Document Type", "value": root._state.defaultDocumentType },
        { "label": "Status", "value": root.structure.statusLabel },
        { "label": "Version", "value": root._state.version }
    ]
    contextFields: [
        { "label": "Parent Structure ID", "value": root._state.parentStructureId },
        { "label": "Sort Order", "value": root._state.sortOrder },
        { "label": "Description", "value": root._state.description },
        { "label": "Notes", "value": root._state.notes },
        { "label": "Active", "value": root._isActive }
    ]
}
