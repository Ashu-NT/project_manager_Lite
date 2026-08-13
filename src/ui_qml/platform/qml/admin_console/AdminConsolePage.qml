pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import identity_access.access 1.0 as PlatformAccess
import Platform.Components 1.0 as PlatformComponents
import identity_access.users 1.0 as UsersDetail
import documents 1.0 as DocumentsDetail
import support.sections 1.0 as SupportSections
import "components" as Components
import "sections" as Sections
import "dialogs" as Dialogs

AppLayouts.WorkspaceFrame {
    id: root

    // -- Public API (backward-compatible) -------------------------
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var workspaceModel: root.platformCatalog
        ? root.platformCatalog.workspace("platform.admin")
        : ({
            "routeId": "platform.admin",
            "title": "Admin Console",
            "summary": ""
        })
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null
    property PlatformControllers.PlatformAdminAccessWorkspaceController accessController: root.platformCatalog
        ? root.platformCatalog.adminAccessWorkspace
        : null
    property PlatformControllers.PlatformSupportWorkspaceController supportController: root.platformCatalog
        ? root.platformCatalog.adminSupportWorkspace
        : null
    property PlatformControllers.PlatformSettingsWorkspaceController settingsController: root.platformCatalog
        ? root.platformCatalog.settingsWorkspace
        : null

    // -- R2 external navigation (PlatformNavigation) ---------------
    // When true, PlatformWorkspace's PlatformNavigation now owns top-level
    // destination selection for this page's sections; the page's own
    // internal AdminNavSidebar is redundant top-level navigation (R2 §9)
    // and is hidden rather than duplicating the new shared rail. The
    // section content itself (list/detail/dialogs) is completely
    // unchanged -- only which control drives `activeSection` changes.
    property bool externallyNavigated: false
    property alias activeSection: adminState.activeSection
    property alias detailOpen: adminState.detailOpen
    property alias entityDetailOpen: adminState.entityDetailOpen
    property alias accessDetailOpen: adminState.accessDetailOpen

    property var userCatalog: root.workspaceController
        ? root.workspaceController.users
        : ({ "title": "Users", "subtitle": "", "emptyState": "", "items": [] })
    property var documentCatalog: root.workspaceController
        ? root.workspaceController.documents
        : ({ "title": "Documents", "subtitle": "", "emptyState": "", "items": [] })
    property var selectedDocument: root.workspaceController
        ? root.workspaceController.selectedDocument
        : ({ "hasSelection": false, "documentId": "", "title": "Select a document",
             "summary": "", "badges": [], "metadataRows": [], "notes": "" })
    property var documentPreviewState: root.workspaceController
        ? root.workspaceController.documentPreview
        : ({ "statusLabel": "No document selected", "summary": "",
             "canOpen": false, "openLabel": "Open Source", "openTargetUrl": "" })
    property var documentLinkCatalog: root.workspaceController
        ? root.workspaceController.documentLinks
        : ({ "title": "Linked Records", "subtitle": "", "emptyState": "", "items": [] })
    property var documentStructureCatalog: root.workspaceController
        ? root.workspaceController.documentStructures
        : ({ "title": "Document Structures", "subtitle": "", "emptyState": "", "items": [] })
    property var moduleEntitlementCatalog: root.settingsController
        ? root.settingsController.moduleEntitlements
        : ({ "title": "Module Entitlements", "subtitle": "", "emptyState": "", "items": [] })

    // -- Python-owned table models ---------------------------------
    property var usersTableModel:             root.workspaceController ? root.workspaceController.usersTableModel             : null
    property var documentsTableModel:         root.workspaceController ? root.workspaceController.documentsTableModel         : null
    property var documentStructuresTableModel:root.workspaceController ? root.workspaceController.documentStructuresTableModel : null

    // -- Navigation & selection state ------------------------------
    property string _activeSection: "users"
    property string _selectedRowId: ""
    property bool _entityDetailOpen: false

    // Roles & Access uses an additive grant detail page (panel stays the list surface).
    property bool _accessDetailOpen: false
    property string _accessGrantId: ""

    AdminWorkspaceState {
        id: adminState
        workspaceController: root.workspaceController
    }

    readonly property bool _detailOpen: {
        const s = adminState.activeSection
        return adminState.entityDetailOpen
            && adminState.selectedRowId.length > 0
            && s !== "access" && s !== "support" && s !== "audit"
    }

    readonly property var _detailItem: {
        const section = adminState.activeSection
        const rowId   = adminState.selectedRowId
        if (!rowId) return null
        let cat = null
        if      (section === "users")         cat = root.userCatalog
        else if (section === "documents")     cat = root.documentCatalog
        else if (section === "structures")    cat = root.documentStructureCatalog
        if (!cat) return null
        const items = cat.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(rowId)) return items[i]
        }
        return null
    }




    function _clearWorkspaceMessages() {
        if (root.workspaceController)
            root.workspaceController.clearMessages()
    }

    function openEntityDetail(sectionId, itemId) {
        adminState.activeSection = String(sectionId || adminState.activeSection || "")
        adminState.selectedRowId = String(itemId || "")
        if (adminState.activeSection === "documents" && adminState.selectedRowId.length > 0) {
            root.inspectDocument(adminState.selectedRowId)
        }
        adminState.entityDetailOpen = adminState.selectedRowId.length > 0
        root._clearWorkspaceMessages()
    }

    function openAdminEntitySection(sectionId, rowId) {
        adminState.activeSection = String(sectionId || "")
        adminState.selectedRowId = rowId ? String(rowId) : ""
        if (adminState.activeSection === "documents" && adminState.selectedRowId.length > 0) {
            root.inspectDocument(adminState.selectedRowId)
        }
        adminState.entityDetailOpen = adminState.selectedRowId.length > 0
        root._clearWorkspaceMessages()
    }

    function closeEntityDetail() {
        adminState.entityDetailOpen = false
        root._clearWorkspaceMessages()
    }

    function handleEntityDetailAction(sectionId, actionId) {
        const id = adminState.selectedRowId
        if (actionId === "show_users") {
            root.openAdminEntitySection("users", "")
            return
        }
        if (actionId === "show_access") {
            root.openAdminEntitySection("access", "")
            return
        }
        if (actionId === "show_documents") {
            root.openAdminEntitySection("documents", "")
            return
        }
        if (actionId === "refresh") {
            if (root.workspaceController) {
                root.workspaceController.refresh()
            }
            return
        }
        if (actionId === "show_audit") {
            root.openAdminEntitySection("audit", "")
            return
        }
        if (actionId === "edit") {
            if      (sectionId === "users")       root.openUserEdit(id)
            else if (sectionId === "documents")   root.openDocumentEdit(id)
            else if (sectionId === "structures")  root.openDocumentStructureEdit(id)
            return
        }
        if (actionId === "toggle_active" && root.workspaceController) {
            if      (sectionId === "users")       root.workspaceController.toggleUserActive(id)
            else if (sectionId === "documents")   root.workspaceController.toggleDocumentActive(id)
            else if (sectionId === "structures")  root.workspaceController.toggleDocumentStructureActive(id)
        }
    }

    function openUserEdit(itemId) {
        const item = adminState.catalogItemById(root.userCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openUserEdit", item.state || {})
    }

    function inspectDocument(itemId) {
        if (root.workspaceController !== null) root.workspaceController.selectDocument(itemId)
    }

    function openDocumentEdit(itemId) {
        const item = adminState.catalogItemById(root.documentCatalog, itemId)
        if (item !== null) {
            root.inspectDocument(itemId)
            dialogHostLoader.invoke("openDocumentEdit", item.state || {})
        }
    }

    function openDocumentLinkCreate() {
        if (root.selectedDocument.hasSelection)
            dialogHostLoader.invoke("openDocumentLinkCreate", root.selectedDocument.documentId || "")
    }

    function openDocumentStructureEdit(itemId) {
        const item = adminState.catalogItemById(root.documentStructureCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openDocumentStructureEdit", item.state || {})
    }

    title: root.workspaceController
        ? (root.workspaceController.overview.title || root.workspaceModel.title)
        : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // -- Shell layout ----------------------------------------------
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // -- Left navigation sidebar -------------------------------
        // Hidden when PlatformNavigation (R2) already owns top-level
        // destination selection for this page -- kept, unmodified, for the
        // route-compatible standalone case (§11) where this page might still
        // be reached directly without the new shell around it.
            Components.AdminNavSidebar {
                id: _sidebar
                visible:               !root.externallyNavigated
                Layout.fillHeight:     true
                Layout.preferredWidth: root.externallyNavigated ? 0 : implicitWidth
                activeSection: adminState.activeSection
                onSectionChanged: function(section) {
                    adminState.activeSection = section
                    adminState.entityDetailOpen = false
                    adminState.selectedRowId = ""
                    root._clearWorkspaceMessages()
                }
            }

        // -- Center workspace --------------------------------------
        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            // -- Users ---------------------------------------------
            PlatformComponents.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "users" && !adminState.detailOpen
                sectionTitle:    "Users"
                entityLabel:     "User"
                catalog:         root.userCatalog
                catalogModel:    root.usersTableModel
                columns:         adminState.userColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openUserCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("users", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // -- Documents -----------------------------------------
            PlatformComponents.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "documents" && !adminState.detailOpen
                sectionTitle:    "Documents"
                entityLabel:     "Document"
                catalog:         root.documentCatalog
                catalogModel:    root.documentsTableModel
                columns:         adminState.documentColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openDocumentCreate")
                onRowSelected:      function(id) {
                    adminState.selectedRowId = id
                    root.inspectDocument(id)
                }
                onRowActivated:     function(id) { root.openEntityDetail("documents", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // -- Document Structures -------------------------------
            PlatformComponents.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "structures" && !adminState.detailOpen
                sectionTitle:    "Document Structures"
                entityLabel:     "Structure"
                catalog:         root.documentStructureCatalog
                catalogModel:    root.documentStructuresTableModel
                columns:         adminState.structureColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openDocumentStructureCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("structures", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            Loader {
                id: userDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "users" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    UsersDetail.AdminUserDetailPage {
                        user: root._detailItem || ({})
                        moduleEntitlementCatalog: root.moduleEntitlementCatalog
                        moduleEntitlementColumns: adminState.moduleColumns
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("users", actionId)
                        }
                    }
                }
            }

            Loader {
                id: documentDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "documents" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    DocumentsDetail.AdminDocumentsDetailPage {
                        document: root._detailItem || ({})
                        selectedDocument: root.selectedDocument
                        documentPreviewState: root.documentPreviewState
                        documentLinkCatalog: root.documentLinkCatalog
                        workspaceController: root.workspaceController
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("documents", actionId)
                        }
                        onDocumentLinkCreateRequested: root.openDocumentLinkCreate()
                    }
                }
            }

            Loader {
                id: structureDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "structures" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    DocumentsDetail.AdminDocumentStructureDetailPage {
                        structure: root._detailItem || ({})
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("structures", actionId)
                        }
                    }
                }
            }

            // -- Roles & Access ------------------------------------
            Item {
                anchors.fill: parent
                visible:      adminState.activeSection === "access"

                PlatformAccess.AccessSecurityPanel {
                    anchors.fill: parent
                    visible:      !adminState.accessDetailOpen
                    controller:   root.accessController
                    onGrantActivated: function(grantId) {
                        adminState.accessGrantId = grantId
                        adminState.accessDetailOpen = true
                    }
                }

                Loader {
                    anchors.fill: parent
                    active:       adminState.activeSection === "access" && adminState.accessDetailOpen
                    visible:      active && status === Loader.Ready
                    asynchronous: true
                    sourceComponent: Component {
                        PlatformAccess.AdminAccessDetailPage {
                            controller:      root.accessController
                            grantId:         adminState.accessGrantId
                            busy:            root.accessController ? root.accessController.isBusy : false
                            errorMessage:    root.accessController ? root.accessController.errorMessage : ""
                            feedbackMessage: root.accessController ? root.accessController.feedbackMessage : ""
                            onBackRequested: adminState.accessDetailOpen = false
                        }
                    }
                }
            }

            // -- Support -------------------------------------------
            SupportSections.AdminSupportSection {
                anchors.fill:      parent
                visible:           adminState.activeSection === "support"
                supportController: root.supportController
            }

            // -- Audit / Overview ----------------------------------
            Sections.AdminAuditSection {
                anchors.fill:        parent
                visible:             adminState.activeSection === "audit"
                workspaceController: root.workspaceController
            }
        }
    }

    // -- Dialog host -----------------------------------------------
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.AdminDialogHost {
                workspaceController: root.workspaceController
            }
        }
    }
}
