// Column configuration for Employee Detail's Documents tab. Every key here
// is a real Document field (see employee_documents_presenter.py's own
// _serialize_document) -- the document id itself is deliberately never
// offered as a column. There is no real "Updated" timestamp on Document
// (only `uploaded_at`, the original upload time) -- the column is labeled
// honestly as "Uploaded" rather than inventing an updated_at the domain
// doesn't track. "Owner / Uploaded By" is deliberately not offered: it
// would require resolving uploaded_by_user_id to a display name for every
// visible row (an N+1 lookup against the User catalog), which has no
// proven need yet for this first vertical slice.

function columns() {
    return [
        { "key": "title",                "label": "Document", "flex": 3,   "minWidth": 180, "sortable": true, "required": true },
        { "key": "documentType",         "label": "Type",      "flex": 1.6, "minWidth": 130 },
        { "key": "businessVersionLabel", "label": "Version",   "flex": 1.2, "minWidth": 100 },
        { "key": "statusLabel",          "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status", "required": true },
        { "key": "uploadedAt",           "label": "Uploaded",  "flex": 1.4, "minWidth": 120 }
    ]
}
