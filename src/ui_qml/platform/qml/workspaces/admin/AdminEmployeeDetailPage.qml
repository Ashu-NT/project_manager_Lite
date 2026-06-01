pragma ComponentBehavior: Bound
import QtQuick

AdminEntityDetailPage {
    id: root

    property var employee: ({})

    readonly property var _state: (root.employee && root.employee.state) ? root.employee.state : ({})
    readonly property bool _isActive: root._state.isActive === true

    entity: root.employee
    fallbackTitle: "Employee"
    contextLabel: "Employment Context"
    contextSubtitle: "Identity-adjacent employee master data aligned to the shared department and site structure."
    contextMessage: "Employees remain platform-owned master records. PM, Maintenance, and other modules should reference them through shared identity and staffing integrations."
    notesTitle: "Employee Notes"
    notesMessage: String(root.employee.supportingText || root.employee.metaText || "")
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
        { "label": "Employee Code", "value": root._state.employeeCode },
        { "label": "Full Name", "value": root._state.fullName || root.employee.title },
        { "label": "Job Title", "value": root._state.title },
        { "label": "Employment Type", "value": root._state.employmentType },
        { "label": "Status", "value": root.employee.statusLabel },
        { "label": "Version", "value": root._state.version }
    ]
    contextFields: [
        { "label": "Department", "value": root._state.departmentName },
        { "label": "Site", "value": root._state.siteName },
        { "label": "Email", "value": root._state.email },
        { "label": "Phone", "value": root._state.phone },
        { "label": "Department ID", "value": root._state.departmentId },
        { "label": "Site ID", "value": root._state.siteId }
    ]
}
