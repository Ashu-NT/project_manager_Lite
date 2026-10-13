// Column configuration for the standalone Parties workspace table. Every
// key here is a real Party field already flattened onto each row's top
// level from `state` by serialize_action_item (see
// party_catalog_presenter.py's _serialize_party). No compound "Code / Type"
// column -- one concept per column. Type and Roles are deliberately
// separate: Type is the ORGANIZATION/INDIVIDUAL identity axis, Roles is the
// multi-valued business-role set (Supplier/Customer/...).

function baseColumns(compactBreakpoint) {
    return [
        { "key": "title",              "label": "Party",               "flex": 2.4, "minWidth": 170, "sortable": true,  "required": true, "visibleByDefault": true },
        { "key": "partyCode",          "label": "Party Code",          "flex": 1.3, "minWidth": 120, "visibleByDefault": true },
        { "key": "partyTypeLabel",     "label": "Type",                "flex": 1.1, "minWidth": 110, "visibleByDefault": true },
        { "key": "rolesLabel",         "label": "Roles",               "flex": 1.8, "minWidth": 160, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "legalName",          "label": "Legal Name",          "flex": 1.8, "minWidth": 160, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "country",            "label": "Country",             "flex": 1.1, "minWidth": 110, "visibleByDefault": true },
        { "key": "statusLabel",        "label": "Status",              "flex": 0,   "minWidth": 90,  "type": "status", "required": true, "visibleByDefault": true },
        { "key": "registrationNumber", "label": "Registration Number", "flex": 1.5, "minWidth": 150, "visibleByDefault": false },
        { "key": "taxIdentifier",      "label": "Tax Identifier",      "flex": 1.4, "minWidth": 140, "visibleByDefault": false },
        { "key": "email",              "label": "Email",               "flex": 1.8, "minWidth": 170, "visibleByDefault": false },
        { "key": "phone",              "label": "Phone",               "flex": 1.3, "minWidth": 130, "visibleByDefault": false },
        { "key": "externalReference",  "label": "External Reference",  "flex": 1.4, "minWidth": 140, "visibleByDefault": false },
        { "key": "updatedAt",          "label": "Updated",             "flex": 1.2, "minWidth": 120, "visibleByDefault": false }
    ]
}

function applyColumnState(base, saved) {
    const order = saved ? (saved.columnOrder || []) : []
    const hidden = saved ? (saved.hiddenColumns || []) : []
    if (order.length === 0) {
        return base.map(function(c) {
            return Object.assign({}, c, { visible: c.visibleByDefault !== false })
        })
    }
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
        if (order.indexOf(base[i].key) < 0) {
            result.push(Object.assign({}, base[i], { visible: base[i].visibleByDefault !== false }))
        }
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
