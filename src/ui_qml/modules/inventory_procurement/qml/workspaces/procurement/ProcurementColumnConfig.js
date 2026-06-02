// Column configuration for Procurement workspace tables

function baseRequisitionColumns() {
    return [
        { "key": "title",           "label": "Requisition",  "flex": 2,   "sortable": true, "required": true },
        { "key": "requisitionCode", "label": "Code",         "flex": 0,   "minWidth": 110, "sortable": true  },
        { "key": "statusLabel",     "label": "Status",       "flex": 0,   "minWidth": 110, "type": "status"  },
        { "key": "supplierLabel",   "label": "Supplier",     "flex": 1.5, "sortable": true  },
        { "key": "totalLabel",      "label": "Total",        "flex": 0,   "minWidth": 100   },
        { "key": "requestedByLabel","label": "Requested By", "flex": 1.2                    },
        { "key": "dueDateLabel",    "label": "Required",     "flex": 0,   "minWidth": 90    }
    ]
}

function basePurchaseOrderColumns() {
    return [
        { "key": "title",        "label": "PO Number",  "flex": 1.5, "sortable": true, "required": true },
        { "key": "statusLabel",  "label": "Status",     "flex": 0,   "minWidth": 110, "type": "status"  },
        { "key": "supplierLabel","label": "Supplier",   "flex": 1.5, "sortable": true  },
        { "key": "totalLabel",   "label": "Total",      "flex": 0,   "minWidth": 100   },
        { "key": "orderDate",    "label": "Order Date", "flex": 0,   "minWidth": 100   },
        { "key": "dueDateLabel", "label": "Due",        "flex": 0,   "minWidth": 90    }
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
