// Column configuration and status filter options for Organization Detail's
// Departments tab (OrganizationDepartmentsSection.qml).

function statusFilterOptions() {
    return [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
}

function columns() {
    return [
        { "key": "title", "label": "Department", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "departmentCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "siteName", "label": "Site", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "departmentType", "label": "Type", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "parentDepartmentName", "label": "Parent Department", "flex": 1, "minWidth": 150, "visible": false },
        { "key": "costCenterCode", "label": "Cost Center", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "createdAt", "label": "Created", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "updatedAt", "label": "Updated", "flex": 1, "minWidth": 140, "visible": false }
    ]
}
