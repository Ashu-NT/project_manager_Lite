// Column configuration for the standalone Employees workspace table.
// Every key here is a real Employee field already flattened onto each
// row's top level from `state` by serialize_action_item (see
// employee_catalog_presenter.py's _serialize_employee) -- the employee id
// itself is deliberately never offered as a column. This workspace is
// scoped to the caller's active Organization (build_catalog_page), so
// Organization is not offered as a column at all. "User Account" is
// deliberately not offered as a column: resolving it for every visible row
// would require an N+1 lookup against the User catalog (EmployeeDto only
// carries a raw user_id), so it stays a per-employee, on-demand resolution
// in the Inspector/Detail Overview's System Access card instead.

function baseColumns(compactBreakpoint) {
    return [
        { "key": "title",          "label": "Employee",       "flex": 2.6, "minWidth": 170, "sortable": true,  "required": true, "visibleByDefault": true },
        { "key": "employeeCode",   "label": "Employee No.",   "flex": 1.4, "minWidth": 130, "visibleByDefault": true },
        { "key": "jobTitle",       "label": "Job Title",      "flex": 1.8, "minWidth": 150, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "departmentName", "label": "Department",     "flex": 2,   "minWidth": 160, "visibleByDefault": true },
        { "key": "siteName",       "label": "Site",            "flex": 1.8, "minWidth": 150, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "employmentType", "label": "Employment Type", "flex": 1.6, "minWidth": 140, "visibleByDefault": true },
        { "key": "statusLabel",    "label": "Status",          "flex": 0,   "minWidth": 90,  "type": "status", "required": true, "visibleByDefault": true },
        { "key": "email",          "label": "Email",           "flex": 2,   "minWidth": 170, "visibleByDefault": false },
        { "key": "phone",          "label": "Phone",           "flex": 1.4, "minWidth": 130, "visibleByDefault": false },
        { "key": "updatedAt",      "label": "Updated",         "flex": 1.4, "minWidth": 130, "visibleByDefault": false }
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
