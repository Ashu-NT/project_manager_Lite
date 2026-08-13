pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Components 1.0 as PlatformComponents
import admin_console.dialogs 1.0 as AdminDialogs

// R4: Organizations as a standalone Platform destination -- list
// (AdminEntityWorkspace, already generic) + inspector (InspectorPanel,
// built in R1, wired here for the first time) + the existing, unchanged
// AdminOrganizationDetailPage for the full detail view. Dialogs reused via
// the existing AdminDialogHost (shared with the Admin Console facade,
// which still owns Users/Documents/Document Structures/Access/Support/
// Audit -- unaffected by this extraction).
AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null

    // Bubbled up to PlatformWorkspacePage so this page can jump to another
    // Platform destination (e.g. the merged Control -> Audit) without
    // depending on the Admin Console facade's own internal sections.
    signal navigateToDestination(string destinationId)

    property var organizationCatalog: root.workspaceController
        ? root.workspaceController.organizations
        : ({ "title": "Organizations", "subtitle": "", "emptyState": "", "items": [] })

    readonly property var _columns: [
        { key: "title",       label: "Name",            flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Timezone", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",          flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Version",         flex: 1, minWidth: 80,  sortable: false, visible: true }
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
        const items = root.organizationCatalog.items || []
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

    function _itemById(itemId) {
        const items = root.organizationCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function _clearMessages() {
        if (root.workspaceController) root.workspaceController.clearMessages()
    }

    function openEdit(itemId) {
        const item = root._itemById(itemId)
        if (item !== null) dialogHostLoader.invoke("openOrganizationEdit", item.state || {})
    }

    function closeDetail() {
        root.detailOpen = false
        root._clearMessages()
    }

    title: "Organizations"
    subtitle: String(root.organizationCatalog.subtitle || "")

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0
            visible: !root.detailOpen

            PlatformComponents.AdminEntityWorkspace {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sectionTitle: "Organizations"
                entityLabel: "Organization"
                catalog: root.organizationCatalog
                catalogModel: root.workspaceController ? root.workspaceController.organizationsTableModel : null
                columns: root._columns
                isBusy: root.busy
                isLoading: root.load
                errorMessage: root.err
                feedbackMessage: root.ok
                selectedRowId: root.selectedRowId

                onCreateRequested: dialogHostLoader.invoke("openOrganizationCreate")
                onRowSelected: function(id) { root.selectedRowId = id }
                onRowActivated: function(id) { root.selectedRowId = id; root.detailOpen = true }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                visible: root.selectedRowId.length > 0
                title: root._selectedItem ? String(root._selectedItem.title || "") : ""
                statusLabel: root._selectedItem ? String(root._selectedItem.statusLabel || "") : ""
                sections: root._inspectorSections
                busy: root.busy
                editActionLabel: "Edit"
                showEditAction: true
                secondaryActionLabel: "Set Active"
                showSecondaryAction: true

                onCloseRequested: root.selectedRowId = ""
                onEditRequested: root.openEdit(root.selectedRowId)
                onSecondaryActionRequested: {
                    if (root.workspaceController) root.workspaceController.setActiveOrganization(root.selectedRowId)
                }
            }
        }

        Loader {
            id: _detailLoader
            anchors.fill: parent
            active: root.detailOpen
            visible: active
            asynchronous: true

            sourceComponent: Component {
                AdminOrganizationDetailPage {
                    organization: root._selectedItem || ({})
                    busy: root.busy
                    errorMessage: root.err
                    feedbackMessage: root.ok

                    onBackRequested: root.closeDetail()

                    onActionRequested: function(actionId) {
                        if (actionId === "edit") {
                            root.openEdit(root.selectedRowId)
                        } else if (actionId === "set_active") {
                            if (root.workspaceController)
                                root.workspaceController.setActiveOrganization(root.selectedRowId)
                        } else if (actionId === "refresh") {
                            if (root.workspaceController)
                                root.workspaceController.refresh()
                        } else if (actionId === "show_audit") {
                            root.navigateToDestination("control_audit")
                        }
                    }
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
