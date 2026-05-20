pragma Singleton

import QtQuick

QtObject {
    // Returns a record-list shape compatible with RecordListCard and list-catalog widgets.
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

    // Returns a bare empty object for unstructured controller-data guards.
    // All template accesses on the result must use || fallbacks
    // (e.g. String(x.someProp || "default")), which the existing workspace code
    // already does for every controller property it reads.
    function emptyObject() {
        return {}
    }
}
