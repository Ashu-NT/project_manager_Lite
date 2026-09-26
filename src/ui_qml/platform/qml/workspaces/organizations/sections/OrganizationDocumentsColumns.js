// Column configuration and status filter options for Organization Detail's
// Documents tab (OrganizationDocumentsSection.qml).

function statusFilterOptions() {
    return [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
}

function columns() {
    return [
        { "key": "title", "label": "Document", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "documentCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "documentType", "label": "Type", "flex": 1, "minWidth": 120, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "businessVersionLabel", "label": "Version", "flex": 1, "minWidth": 100, "visible": false },
        { "key": "isCurrent", "label": "Current", "flex": 0, "minWidth": 90, "visible": false },
        { "key": "fileName", "label": "File", "flex": 1, "minWidth": 160, "visible": false }
    ]
}
