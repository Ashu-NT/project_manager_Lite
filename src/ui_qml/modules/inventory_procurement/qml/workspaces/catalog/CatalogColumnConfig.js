// Column configuration for Catalog workspace tables

function baseItemColumns() {
    return [
        { "key": "title",         "label": "Item Name",  "flex": 2,   "sortable": true, "required": true },
        { "key": "itemCode",      "label": "Code",       "flex": 0,   "minWidth": 110, "sortable": true  },
        { "key": "categoryLabel", "label": "Category",   "flex": 1.5, "sortable": true  },
        { "key": "statusLabel",   "label": "Status",     "flex": 0,   "minWidth": 90,  "type": "status"  }
    ]
}

function baseCategoryColumns() {
    return [
        { "key": "title",       "label": "Category", "flex": 2,   "sortable": true, "required": true },
        { "key": "code",        "label": "Code",     "flex": 0,   "minWidth": 100, "sortable": true  },
        { "key": "typeLabel",   "label": "Type",     "flex": 1,   "sortable": true  },
        { "key": "statusLabel", "label": "Status",   "flex": 0,   "minWidth": 90,  "type": "status"  }
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
