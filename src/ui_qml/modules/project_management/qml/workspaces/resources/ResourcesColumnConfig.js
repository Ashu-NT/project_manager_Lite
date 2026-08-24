// Column configuration for Resources workspace table

function baseColumns() {
    return [
        { "key": "resourceCode",    "label": "Code",          "flex": 0,   "minWidth": 112, "sortable": true, "required": true, "visibleByDefault": true },
        { "key": "title",           "label": "Resource",      "flex": 2,   "sortable": true, "required": true, "visibleByDefault": true },
        { "key": "workerTypeLabel", "label": "Engagement",    "flex": 1,   "sortable": true,                  "visibleByDefault": true },
        { "key": "role",            "label": "Role",          "flex": 1.2, "sortable": true,                  "visibleByDefault": true },
        { "key": "organization",    "label": "Organization",  "flex": 1.2, "sortable": false,                 "visibleByDefault": false },
        { "key": "department",      "label": "Department",    "flex": 1.2, "sortable": true,                  "visibleByDefault": true },
        { "key": "site",            "label": "Site",          "flex": 1,   "sortable": true,                  "visibleByDefault": false },
        { "key": "statusLabel",     "label": "Status",        "flex": 0,   "minWidth": 96, "type": "status", "sortable": true, "required": true, "visibleByDefault": true },
        { "key": "capacityPercent", "label": "Capacity Mod.", "flex": 0,   "minWidth": 112, "sortable": true, "visibleByDefault": true }
    ]
}

function applyColumnState(base, saved) {
    const order = saved ? (saved.columnOrder || []) : []
    const hidden = saved ? (saved.hiddenColumns || []) : []
    if (order.length === 0) return base.slice()
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
        if (order.indexOf(base[i].key) < 0) result.push(Object.assign({}, base[i]))
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

function visibleColumnsForExport(columns) {
    return columns.filter(function(c) { return c.visible !== false })
        .map(function(c) { return { "key": c.key, "label": c.label } })
}
