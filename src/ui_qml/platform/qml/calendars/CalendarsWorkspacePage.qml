pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import App.Theme 1.0 as Theme
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents
import Platform.Dialogs 1.0 as AdminDialogs

// R4: Calendars as a standalone Platform destination. Same list+inspector
// shell as the other 5 entities, but the full detail page
// (AdminCalendarDetailPage) is materially richer -- working rules,
// exceptions, recurring events, assignments -- and is reused verbatim via
// its existing direct-signal contract (no generic actionId dispatch).
// No "Toggle" secondary action here: PlatformAdminWorkspaceController has
// no toggleCalendarActive method at all (confirmed) -- showing one would
// be a dead, unwireable button, so it's omitted rather than faked.
AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    signal navigateToDestination(string destinationId)

    function openRecord(rowId) {
        root.selectedRowId = String(rowId || "")
        root.detailOpen = root.selectedRowId.length > 0
    }

    property var calendarCatalog: root.workspaceController
        ? root.workspaceController.calendars
        : ({ "title": "Calendars", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _columns: [
        { key: "title",       label: "Calendar",     flex: 2.2, minWidth: 180, sortable: true,  visible: true },
        { key: "subtitle",    label: "Working Days", flex: 3.0, minWidth: 220, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",       flex: 0,   minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Ownership",    flex: 2.4, minWidth: 180, sortable: false, visible: true, hideBelow: Theme.AppTheme.compactContentBreakpoint }
    ]

    property string selectedRowId: ""
    property bool detailOpen: false

    readonly property bool   busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property var _selectedItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.calendarCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _inspectorSections: {
        const item = root._selectedItem
        if (!item) return []
        return [
            { "label": "Details", "value": String(item.subtitle || "") },
            { "label": "Info", "value": String(item.metaText || "") }
        ]
    }

    readonly property var _detailContext: {
        const item = root._selectedItem
        if (!root.workspaceController || !item) return ({ "workingRules": [], "exceptions": [], "recurringEvents": [], "assignments": {} })
        const state = item.state || {}
        const calendarId = String(state.calendarId || state.id || item.id || "")
        if (!calendarId.length) return ({ "workingRules": [], "exceptions": [], "recurringEvents": [], "assignments": {} })
        return root.workspaceController.calendarDetailContext(calendarId)
    }

    readonly property string _calendarId: {
        const item = root._selectedItem
        const state = item && item.state ? item.state : {}
        return String(state.calendarId || state.id || (item ? item.id : "") || "")
    }

    function _itemById(itemId) {
        const items = root.calendarCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openCalendarEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    title: "Calendars"
    subtitle: String(root.calendarCatalog.subtitle || "")

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0
            visible: !root.detailOpen

            PlatformComponents.AdminEntityWorkspace {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Calendars"
                entityLabel: "Calendar"
                catalog: root.calendarCatalog
                catalogModel: root.workspaceController ? root.workspaceController.calendarsTableModel : null
                columns: root._columns
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId

                onCreateRequested: dialogHostLoader.invoke("openCalendarCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                visible: root.selectedRowId.length > 0 && Window.width >= Theme.AppTheme.compactContentBreakpoint
                title: root._selectedItem ? String(root._selectedItem.title || "") : ""
                statusLabel: root._selectedItem ? String(root._selectedItem.statusLabel || "") : ""
                sections: root._inspectorSections
                busy: root.busy
                editActionLabel: "Edit"
                showEditAction: true
                showSecondaryAction: false

                onCloseRequested: root.selectedRowId = ""
                onEditRequested: root.openEdit(root.selectedRowId)
            }
        }

        Loader {
            anchors.fill: parent
            active: root.detailOpen
            visible: active
            asynchronous: true

            sourceComponent: Component {
                AdminCalendarDetailPage {
                    workspaceController: root.workspaceController
                    calendar: root._selectedItem || ({})
                    workingRules: root._detailContext.workingRules || []
                    enterpriseExceptions: root._detailContext.exceptions || []
                    recurringEvents: root._detailContext.recurringEvents || []
                    assignments: root._detailContext.assignments || ({})
                    busy: root.busy
                    errorMessage: root.err
                    feedbackMessage: root.ok
                    isEnterpriseCalendar: {
                        const item = root._selectedItem
                        return item && item.state ? item.state.isEnterpriseCalendar === true : false
                    }

                    onBackRequested: root.closeDetail()
                    onEditRequested: root.openEdit(root.selectedRowId)
                    onAddExceptionRequested: dialogHostLoader.invoke("openCalendarExceptionCreate", root._calendarId)
                    onAddRecurringEventRequested: dialogHostLoader.invoke("openCalendarRecurringEventCreate", root._calendarId)
                    onOpenAuditRequested: root.navigateToDestination("control_audit")
                }
            }
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            AdminDialogs.AdminDialogHost {
                workspaceController: root.workspaceController
            }
        }
    }
}
