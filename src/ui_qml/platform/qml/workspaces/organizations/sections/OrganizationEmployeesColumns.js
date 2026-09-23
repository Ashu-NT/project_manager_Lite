// Column configuration and status filter options for Organization Detail's
// Employees tab (OrganizationEmployeesSection.qml).

function statusFilterOptions() {
    return [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
}

function columns() {
    return [
        { "key": "title", "label": "Employee", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "employeeCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "departmentName", "label": "Department", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "siteName", "label": "Site", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "employmentType", "label": "Employment Type", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "email", "label": "Email", "flex": 1, "minWidth": 160, "visible": false }
    ]
}
