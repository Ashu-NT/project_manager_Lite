// Column configuration for Work Orders workspace table

function baseColumns() {
    return [
        { "key": "title",              "label": "Code",     "flex": 1,   "sortable": true  },
        { "key": "subtitle",           "label": "Title",    "flex": 2,   "sortable": true  },
        { "key": "statusLabel",        "label": "Status",   "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "priorityLabel",      "label": "Priority", "flex": 0,   "minWidth": 90,  "type": "status" },
        { "key": "workOrderTypeLabel", "label": "Type",     "flex": 1,   "sortable": true  },
        { "key": "assetLabel",         "label": "Asset",    "flex": 1.5                    },
        { "key": "plannedStart",       "label": "Planned",  "flex": 0,   "minWidth": 100   }
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
