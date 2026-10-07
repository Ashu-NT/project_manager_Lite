// Column configuration for the standalone Calendars workspace table.
// Every key here is a real Calendar field already flattened onto each row's
// top level from `state` by serialize_action_item (see
// calendar_catalog_presenter.py's _serialize_calendar). Calendar cardinality
// per Organization is small and bounded (a handful, not thousands) -- the
// list is loaded in full and filtered/sorted locally, matching the backend's
// own non-paginated list_calendars() read model; no server-side pagination
// is introduced here merely for visual consistency with larger catalogs.

function baseColumns(compactBreakpoint) {
    return [
        { "key": "title",            "label": "Calendar",      "flex": 2.2, "minWidth": 180, "sortable": true,  "required": true, "visibleByDefault": true },
        { "key": "code",             "label": "Code",          "flex": 1.1, "minWidth": 110, "visibleByDefault": true },
        { "key": "timeZone",         "label": "Time Zone",     "flex": 1.6, "minWidth": 150, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "workingWeekLabel", "label": "Working Week",  "flex": 1.6, "minWidth": 140, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "typeLabel",        "label": "Type",          "flex": 1.2, "minWidth": 120, "visibleByDefault": true },
        { "key": "statusLabel",      "label": "Status",        "flex": 0,   "minWidth": 90,  "type": "status", "required": true, "visibleByDefault": true },
        { "key": "effectiveFrom",    "label": "Effective From", "flex": 1.3, "minWidth": 130, "visibleByDefault": false },
        { "key": "effectiveTo",      "label": "Effective To",   "flex": 1.3, "minWidth": 130, "visibleByDefault": false },
        { "key": "usageLabel",       "label": "Usage",          "flex": 1.2, "minWidth": 120, "visibleByDefault": false },
        { "key": "updatedAt",        "label": "Updated",        "flex": 1.6, "minWidth": 140, "visibleByDefault": false }
    ]
}

function applyColumnState(base, saved) {
    const order = saved ? (saved.columnOrder || []) : []
    const hidden = saved ? (saved.hiddenColumns || []) : []
    if (order.length === 0) {
        return base.map(function(c) {
            return Object.assign({}, c, { visible: c.visibleByDefault !== false })
        })
    }
    const hiddenSet = {}
    for (let i = 0; i < hidden.length; i++) hiddenSet[hidden[i]] = true
    const byKey = {}
    for (let i = 0; i < base.length; i++) byKey[base[i].key] = base[i]
    const result = []
    for (let j = 0; j < order.length; j++) {
        const col = byKey[order[j]]
        if (!col) continue
        const c = Object.assign({}, col)
        if (c.required !== true) c.visible = !hiddenSet[order[j]]
        result.push(c)
    }
    for (let i = 0; i < base.length; i++) {
        if (order.indexOf(base[i].key) < 0) {
            result.push(Object.assign({}, base[i], { visible: base[i].visibleByDefault !== false }))
        }
    }
    return result
}

function buildColumnState(columns) {
    const order = []
    const hidden = []
    for (let i = 0; i < columns.length; i++) {
        order.push(columns[i].key)
        if (columns[i].visible === false) hidden.push(columns[i].key)
    }
    return { "columnOrder": order, "hiddenColumns": hidden }
}
