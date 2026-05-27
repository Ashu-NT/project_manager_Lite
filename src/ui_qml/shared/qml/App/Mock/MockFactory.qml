pragma Singleton

import QtQuick

QtObject {
    // ── catalog ──────────────────────────────────────────────────────────────
    // Record-list shape — used by RecordListCard and list-catalog widgets.
    // title:      header label shown in the card
    // subtitle:   optional sub-label (defaults to "")
    // emptyState: message shown when items is empty (defaults to "")
    function catalog(title, subtitle, emptyState) {
        return {
            "title":      title      || "",
            "subtitle":   subtitle   || "",
            "emptyState": emptyState || "",
            "items":      []
        }
    }

    // ── detail ───────────────────────────────────────────────────────────────
    // Standard record-detail/inspector shape — used by detail section panels.
    // emptyState: placeholder shown when no record is selected (defaults to "")
    function detail(emptyState) {
        return {
            "id":          "",
            "title":       "",
            "statusLabel": "",
            "subtitle":    "",
            "description": "",
            "emptyState":  emptyState || "",
            "fields":      [],
            "state":       {}
        }
    }

    // ── fieldCatalog ─────────────────────────────────────────────────────────
    // Field-table shape — like catalog but with a fields array instead of items.
    // Used by summary cards and tabular views that render field/value rows.
    function fieldCatalog(title, subtitle, emptyState) {
        return {
            "title":      title      || "",
            "subtitle":   subtitle   || "",
            "emptyState": emptyState || "",
            "fields":     []
        }
    }

    // ── fieldRecord ──────────────────────────────────────────────────────────
    // Field-record shape — like fieldCatalog but includes a state bag.
    // Used by timesheet review details, assignment summaries, and similar views
    // that render field/value rows alongside a mutable state object.
    function fieldRecord(title, subtitle, emptyState) {
        return {
            "title":      title      || "",
            "subtitle":   subtitle   || "",
            "emptyState": emptyState || "",
            "fields":     [],
            "state":      {}
        }
    }

    // ── emptyObject ──────────────────────────────────────────────────────────
    // Bare empty object — safe placeholder for unstructured controller data.
    // All template accesses on the result must use || fallbacks
    // (e.g. String(x.someProp || "default")), which existing workspace code
    // already does for every controller property it reads.
    function emptyObject() {
        return {}
    }
}
