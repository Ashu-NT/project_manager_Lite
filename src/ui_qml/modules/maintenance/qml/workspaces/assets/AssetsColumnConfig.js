// Column configuration for Assets workspace table

function baseColumns() {
    return [
        { "key": "title",        "label": "Asset",    "flex": 2,   "sortable": true, "required": true },
        { "key": "assetCode",    "label": "Code",     "flex": 0,   "minWidth": 100, "sortable": true  },
        { "key": "statusLabel",  "label": "Status",   "flex": 0,   "minWidth": 100, "type": "status"  },
        { "key": "assetType",    "label": "Type",     "flex": 1,   "sortable": true  },
        { "key": "location",     "label": "Location", "flex": 1.5, "sortable": true  },
        { "key": "system",       "label": "System",   "flex": 1.2, "sortable": true  }
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
