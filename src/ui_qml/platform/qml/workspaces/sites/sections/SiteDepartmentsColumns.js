// Column configuration for Site Detail's own Departments tab. Every key is
// a real Department field already flattened onto each row's top level from
// `state` (see department_catalog_presenter.py's _serialize_department).
// No Site column -- the entire section is already scoped to one site.

function statusFilterOptions() {
    return [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
}

function baseColumns(compactBreakpoint) {
    return [
        { "key": "title",                "label": "Department",       "flex": 3,   "minWidth": 160, "sortable": true,  "required": true, "visibleByDefault": true },
        { "key": "departmentCode",       "label": "Code",             "flex": 1.2, "minWidth": 120, "visibleByDefault": true },
        { "key": "departmentType",       "label": "Type",             "flex": 1.4, "minWidth": 120, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "statusLabel",          "label": "Status",           "flex": 0,   "minWidth": 90,  "type": "status", "required": true, "visibleByDefault": true },
        { "key": "costCenterCode",       "label": "Cost Center",      "flex": 1.2, "minWidth": 120, "visibleByDefault": false },
        { "key": "parentDepartmentName", "label": "Parent Department","flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "updatedAt",            "label": "Updated",          "flex": 1.6, "minWidth": 140, "visibleByDefault": false }
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

// Legacy entry point kept for the standalone Sites workspace's Departments
// tab (SitesWorkspacePage.qml), which does not yet have its own column
// customizer -- returns the fixed default-visible set only.
function columns() {
    return baseColumns(760).filter(function(c) { return c.visibleByDefault !== false })
}
