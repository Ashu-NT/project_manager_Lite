pragma ComponentBehavior: Bound
import QtQuick
import Platform.Controllers 1.0 as PlatformControllers

Item {
    id: root

    // ── Injected ──────────────────────────────────────────────────────────
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController

    // ── UI state ──────────────────────────────────────────────────────────
    property string activeSection:      "organizations"
    property string selectedRowId:      ""
    property bool   entityDetailOpen:   false
    property bool   accessDetailOpen:   false
    property string accessGrantId:      ""

    // ── Computed ──────────────────────────────────────────────────────────
    readonly property bool detailOpen: root.entityDetailOpen
        && root.selectedRowId.length > 0
        && root.activeSection !== "access"
        && root.activeSection !== "support"
        && root.activeSection !== "audit"

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy        : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading     : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage  : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    // ── Column definitions ────────────────────────────────────────────────
    readonly property var orgColumns: [
        { key: "title",       label: "Name",            flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Timezone", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",          flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Version",         flex: 1, minWidth: 80,  sortable: false, visible: true }
    ]
    readonly property var calendarColumns: [
        { key: "title",       label: "Calendar",     flex: 2.2, minWidth: 180, sortable: true,  visible: true },
        { key: "subtitle",    label: "Working Days", flex: 3.0, minWidth: 220, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",       flex: 0,   minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Ownership",    flex: 2.4, minWidth: 180, sortable: false, visible: true }
    ]
    readonly property var siteColumns: [
        { key: "title",       label: "Name",            flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Location", flex: 4, minWidth: 200, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",          flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Timezone / FX",   flex: 2, minWidth: 150, sortable: false, visible: true }
    ]
    readonly property var deptColumns: [
        { key: "title",       label: "Name",        flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Cost Center", flex: 2, minWidth: 120, sortable: false, visible: true }
    ]
    readonly property var employeeColumns: [
        { key: "title",       label: "Name",             flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Job Title", flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",           flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Employment",       flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
    readonly property var userColumns: [
        { key: "title",       label: "Display Name", flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Username",     flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",       flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Security",     flex: 3, minWidth: 180, sortable: false, visible: true }
    ]
    readonly property var partyColumns: [
        { key: "title",       label: "Name",        flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Legal Name",  flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
    readonly property var documentColumns: [
        { key: "title",       label: "Title",       flex: 3, minWidth: 180, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Storage",     flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
    readonly property var moduleColumns: [
        { key: "title",       label: "Module",          flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Stage / License", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Lifecycle",       flex: 0, minWidth: 100, sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Runtime",         flex: 3, minWidth: 200, sortable: false, visible: true }
    ]
    readonly property var structureColumns: [
        { key: "title",       label: "Name",        flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Info",        flex: 2, minWidth: 120, sortable: false, visible: true }
    ]

    // ── Helpers ───────────────────────────────────────────────────────────
    function catalogItemById(catalog, itemId) {
        const items = catalog.items || []
        for (let i = 0; i < items.length; i++) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }
}
