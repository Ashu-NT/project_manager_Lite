// Column configuration for Work Requests workspace table

function baseColumns() {
    return [
        { "key": "title",              "label": "Code",        "flex": 1,   "sortable": true  },
        { "key": "subtitle",           "label": "Description", "flex": 2,   "sortable": true  },
        { "key": "statusLabel",        "label": "Status",      "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "priorityLabel",      "label": "Priority",    "flex": 0,   "minWidth": 90,  "type": "status" },
        { "key": "requestTypeLabel",   "label": "Type",        "flex": 1,   "sortable": true  },
        { "key": "assetLabel",         "label": "Asset",       "flex": 1.5                    },
        { "key": "submittedAt",        "label": "Submitted",   "flex": 0,   "minWidth": 100   }
    ]
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
