// Column configuration for Preventive Maintenance workspace table

function baseColumns() {
    return [
        { "key": "title",        "label": "Plan",      "flex": 2,   "sortable": true, "required": true },
        { "key": "planCode",     "label": "Code",      "flex": 0,   "minWidth": 100, "sortable": true  },
        { "key": "statusLabel",  "label": "Status",    "flex": 0,   "minWidth": 100, "type": "status"  },
        { "key": "frequency",    "label": "Frequency", "flex": 1,   "sortable": true  },
        { "key": "assetLabel",   "label": "Asset",     "flex": 1.5, "sortable": true  },
        { "key": "nextDueLabel", "label": "Next Due",  "flex": 0,   "minWidth": 100   }
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
