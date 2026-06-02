// Column configuration for Inventory workspace table

function baseColumns() {
    return [
        { "key": "title",            "label": "Item",       "flex": 2,   "sortable": true, "required": true },
        { "key": "itemCode",         "label": "Code",       "flex": 0,   "minWidth": 110, "sortable": true  },
        { "key": "statusLabel",      "label": "Status",     "flex": 0,   "minWidth": 90,  "type": "status"  },
        { "key": "locationLabel",    "label": "Location",   "flex": 1.5, "sortable": true  },
        { "key": "quantityOnHand",   "label": "On Hand",    "flex": 0,   "minWidth": 80    },
        { "key": "quantityReserved", "label": "Reserved",   "flex": 0,   "minWidth": 80    },
        { "key": "quantityAvailable","label": "Available",  "flex": 0,   "minWidth": 80    }
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
