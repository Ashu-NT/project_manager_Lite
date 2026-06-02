// Column configuration for Warehouses workspace table

function baseColumns() {
    return [
        { "key": "title",        "label": "Warehouse",  "flex": 2,   "sortable": true, "required": true },
        { "key": "code",         "label": "Code",       "flex": 0,   "minWidth": 100, "sortable": true  },
        { "key": "statusLabel",  "label": "Status",     "flex": 0,   "minWidth": 90,  "type": "status"  },
        { "key": "siteLabel",    "label": "Site",       "flex": 1.5, "sortable": true  },
        { "key": "locationCount","label": "Locations",  "flex": 0,   "minWidth": 80    }
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
