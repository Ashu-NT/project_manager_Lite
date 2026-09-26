// Column configuration for the Organizations workspace table.
// Every key here is a real Organization field auto-flattened onto each row's
// top level from `state` by serialize_action_item (see organization_catalog_
// presenter.py's _serialize_organization) -- the organization id itself is
// deliberately never offered as a column.

function baseColumns(compactBreakpoint) {
    return [
        { "key": "title",              "label": "Organization",         "flex": 3,   "minWidth": 160, "sortable": true,  "required": true, "visibleByDefault": true },
        { "key": "organizationCode",   "label": "Code",                 "flex": 1,   "minWidth": 110, "visibleByDefault": true },
        { "key": "statusLabel",        "label": "Status",               "flex": 0,   "minWidth": 90,  "type": "status", "required": true, "visibleByDefault": true },
        { "key": "location",           "label": "Country / Location",   "flex": 2,   "minWidth": 150, "hideBelow": compactBreakpoint, "visibleByDefault": true },
        { "key": "city",               "label": "City",                 "flex": 2,   "minWidth": 120, "visibleByDefault": false },
        { "key": "countryName",        "label": "Country",              "flex": 1,   "minWidth": 120, "visibleByDefault": false },
        { "key": "countryCode",        "label": "Country Code",         "flex": 0,   "minWidth": 90,  "visibleByDefault": false },
        { "key": "legalName",          "label": "Legal Name",           "flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "registrationNumber", "label": "Registration Number",  "flex": 1,   "minWidth": 140, "visibleByDefault": false },
        { "key": "taxId",              "label": "Tax / VAT ID",         "flex": 1,   "minWidth": 130, "visibleByDefault": false },
        { "key": "timezoneName",       "label": "Timezone",             "flex": 1,   "minWidth": 130, "visibleByDefault": false },
        { "key": "baseCurrency",       "label": "Base Currency",        "flex": 0,   "minWidth": 100, "visibleByDefault": false },
        { "key": "addressLine1",       "label": "Address Line 1",       "flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "addressLine2",       "label": "Address Line 2",       "flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "postalCode",         "label": "Postal Code",          "flex": 0,   "minWidth": 100, "visibleByDefault": false },
        { "key": "stateRegion",        "label": "State / Region",       "flex": 1,   "minWidth": 130, "visibleByDefault": false },
        { "key": "email",              "label": "Email",                "flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "phone",              "label": "Phone",                "flex": 1,   "minWidth": 130, "visibleByDefault": false },
        { "key": "website",            "label": "Website",              "flex": 2,   "minWidth": 160, "visibleByDefault": false },
        { "key": "version",            "label": "Version",              "flex": 0,   "minWidth": 90,  "visibleByDefault": false }
    ]
}

function applyColumnState(base, saved) {
    const order = saved ? (saved.columnOrder || []) : []
    const hidden = saved ? (saved.hiddenColumns || []) : []
    if (order.length === 0) {
        // Nothing saved yet -- start from each column's own default rather
        // than leaving `visible` unset, which DataTable would otherwise
        // treat as visible regardless of visibleByDefault.
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
        // A column added to baseColumns() after this user's saved state was
        // written (never in their columnOrder) still needs its own default
        // applied, or it would render as visible regardless of
        // visibleByDefault -- same reasoning as the no-saved-state branch.
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
