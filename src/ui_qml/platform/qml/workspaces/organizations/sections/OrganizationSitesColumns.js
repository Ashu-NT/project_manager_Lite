// Column configuration and status filter options for Organization Detail's
// Sites tab (OrganizationSitesSection.qml).

function statusFilterOptions() {
    return [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
}

function columns() {
    return [
        { "key": "title", "label": "Site", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "siteCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "location", "label": "Location", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "country", "label": "Country", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "timezoneName", "label": "Time Zone", "flex": 1, "minWidth": 130, "visible": false },
        { "key": "createdAt", "label": "Created", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "updatedAt", "label": "Updated", "flex": 1, "minWidth": 140, "visible": false }
    ]
}
