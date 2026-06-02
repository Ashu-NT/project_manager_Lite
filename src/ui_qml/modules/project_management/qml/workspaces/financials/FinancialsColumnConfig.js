// Column configuration for Financials workspace cost register table

function baseColumns() {
    return [
        { "key": "title",             "label": "Description",   "flex": 2,   "sortable": true, "required": true, "visibleByDefault": true },
        { "key": "costCode",          "label": "Code",          "flex": 0,   "minWidth": 100, "sortable": true,  "visibleByDefault": true },
        { "key": "costTypeLabel",     "label": "Type",          "flex": 0,   "minWidth": 110, "type": "status",  "visibleByDefault": true },
        { "key": "commitmentLabel",   "label": "Commitment",    "flex": 0,   "minWidth": 110, "type": "status",  "visibleByDefault": true },
        { "key": "taskTitle",         "label": "Task",          "flex": 1.5, "sortable": true,                   "visibleByDefault": true },
        { "key": "budgetLabel",       "label": "Budget",        "flex": 0,   "minWidth": 90,                     "visibleByDefault": true },
        { "key": "forecastLabel",     "label": "Forecast",      "flex": 0,   "minWidth": 90,                     "visibleByDefault": true },
        { "key": "actualLabel",       "label": "Actual",        "flex": 0,   "minWidth": 90,                     "visibleByDefault": true },
        { "key": "committedLabel",    "label": "Committed",     "flex": 0,   "minWidth": 90,                     "visibleByDefault": false },
        { "key": "dateLabel",         "label": "Date",          "flex": 0,   "minWidth": 90,                     "visibleByDefault": true }
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
