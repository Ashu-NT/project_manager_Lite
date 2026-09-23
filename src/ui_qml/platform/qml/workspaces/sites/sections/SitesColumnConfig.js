// Column configuration for the standalone Sites workspace table.
// Every key here is a real Site field already flattened onto each row's top
// level from `state` by serialize_action_item (see site_catalog_presenter.py's
// _serialize_site) -- the site id itself is deliberately never offered as a
// column. This workspace is scoped to the caller's active Organization
// (build_catalog_page), so Organization is an optional column, not default.

function baseColumns(compactBreakpoint) {
    return [
        { "key": "title",            "label": "Site",         "flex": 3,   "minWidth": 160, "sortable": true,  "required": true, "visibleByDefault": true },
        { "key": "siteCode",         "label": "Code",         "flex": 1.2, "minWidth": 120, "visibleByDefault": true },
        { "key": "siteType",         "label": "Type",         "flex": 1.4, "minWidth": 120, "visibleByDefault": true },
        { "key": "location",         "label": "Location",     "flex": 2.2, "minWidth": 170, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "statusLabel",      "label": "Status",       "flex": 0,   "minWidth": 90,  "type": "status", "required": true, "visibleByDefault": true },
        { "key": "timezoneName",     "label": "Time Zone",    "flex": 1.6, "minWidth": 140, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "organizationName", "label": "Organization", "flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "currencyCode",     "label": "Currency",     "flex": 1,   "minWidth": 100, "visibleByDefault": false },
        { "key": "country",          "label": "Country",      "flex": 1.4, "minWidth": 120, "visibleByDefault": false },
        { "key": "createdAt",        "label": "Created",      "flex": 1.6, "minWidth": 140, "visibleByDefault": false },
        { "key": "updatedAt",        "label": "Updated",      "flex": 1.6, "minWidth": 140, "visibleByDefault": false }
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
