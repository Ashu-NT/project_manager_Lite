function baseColumns() {
    return [
        { "key": "date", "label": "Date", "minWidth": 110, "sortable": true, "visibleByDefault": true },
        { "key": "project", "label": "Project", "flex": 1.2, "sortable": true, "visibleByDefault": true },
        { "key": "task", "label": "Task / Activity", "flex": 1.5, "sortable": true, "visibleByDefault": true },
        { "key": "hours", "label": "Hours", "minWidth": 90, "sortable": true, "visibleByDefault": true },
        { "key": "description", "label": "Description", "flex": 2, "sortable": false, "visibleByDefault": true }
    ]
}

function historyColumns() {
    return [
        { "key": "periodLabel", "label": "Period", "flex": 1.5, "sortable": false, "visibleByDefault": true },
        { "key": "statusLabel", "label": "Status", "type": "status", "minWidth": 130, "sortable": false, "visibleByDefault": true },
        { "key": "totalHoursLabel", "label": "Hours", "minWidth": 90, "sortable": false, "visibleByDefault": true },
        { "key": "entryCount", "label": "Entries", "minWidth": 90, "sortable": false, "visibleByDefault": true },
        { "key": "submittedAtLabel", "label": "Submitted", "flex": 1.2, "sortable": false, "visibleByDefault": true }
    ]
}
