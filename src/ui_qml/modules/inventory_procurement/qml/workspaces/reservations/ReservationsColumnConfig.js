// Column configuration for Reservations workspace table

function baseColumns() {
    return [
        { "key": "title",            "label": "Reservation",  "flex": 2,   "sortable": true, "required": true },
        { "key": "reservationCode",  "label": "Code",         "flex": 0,   "minWidth": 110, "sortable": true  },
        { "key": "statusLabel",      "label": "Status",       "flex": 0,   "minWidth": 110, "type": "status"  },
        { "key": "itemLabel",        "label": "Item",         "flex": 1.5, "sortable": true  },
        { "key": "quantityLabel",    "label": "Qty",          "flex": 0,   "minWidth": 80    },
        { "key": "sourceLabel",      "label": "Source",       "flex": 1.5                    },
        { "key": "requiredDateLabel","label": "Required",     "flex": 0,   "minWidth": 90    }
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
