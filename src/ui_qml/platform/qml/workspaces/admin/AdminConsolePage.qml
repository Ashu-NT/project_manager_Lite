pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API (backward-compatible) ─────────────────────────
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
    property var organizationCatalog: root.workspaceController
        ? root.workspaceController.organizations
        : ({ "title": "Organizations", "subtitle": "", "emptyState": "", "items": [] })
    property var siteCatalog: root.workspaceController
        ? root.workspaceController.sites
        : ({ "title": "Sites", "subtitle": "", "emptyState": "", "items": [] })
    property var departmentCatalog: root.workspaceController
        ? root.workspaceController.departments
        : ({ "title": "Departments", "subtitle": "", "emptyState": "", "items": [] })
    property var employeeCatalog: root.workspaceController
        ? root.workspaceController.employees
        : ({ "title": "Employees", "subtitle": "", "emptyState": "", "items": [] })
    property var userCatalog: root.workspaceController
        ? root.workspaceController.users
        : ({ "title": "Users", "subtitle": "", "emptyState": "", "items": [] })
    property var partyCatalog: root.workspaceController
        ? root.workspaceController.parties
        : ({ "title": "Parties", "subtitle": "", "emptyState": "", "items": [] })
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

    // ── Python-owned table models ─────────────────────────────────
    property var organizationsTableModel:     root.workspaceController ? root.workspaceController.organizationsTableModel     : null
    property var sitesTableModel:             root.workspaceController ? root.workspaceController.sitesTableModel             : null
    property var departmentsTableModel:       root.workspaceController ? root.workspaceController.departmentsTableModel       : null
    property var employeesTableModel:         root.workspaceController ? root.workspaceController.employeesTableModel         : null
    property var usersTableModel:             root.workspaceController ? root.workspaceController.usersTableModel             : null
    property var partiesTableModel:           root.workspaceController ? root.workspaceController.partiesTableModel           : null
    property var documentsTableModel:         root.workspaceController ? root.workspaceController.documentsTableModel         : null
    property var documentStructuresTableModel:root.workspaceController ? root.workspaceController.documentStructuresTableModel : null

    // ── Navigation & selection state ──────────────────────────────
    property string _activeSection: "organizations"
    property string _selectedRowId: ""
    property bool _entityDetailOpen: false

    // Roles & Access uses an additive grant detail page (panel stays the list surface).
    property bool _accessDetailOpen: false
    property string _accessGrantId: ""

    readonly property bool _detailOpen: {
        const s = root._activeSection
        return root._entityDetailOpen
            && root._selectedRowId.length > 0
            && s !== "access" && s !== "support" && s !== "audit"
    }

    readonly property var _detailItem: {
        const section = root._activeSection
        const rowId   = root._selectedRowId
        if (!rowId) return null
        let cat = null
        if      (section === "organizations") cat = root.organizationCatalog
        else if (section === "sites")         cat = root.siteCatalog
        else if (section === "departments")   cat = root.departmentCatalog
        else if (section === "employees")     cat = root.employeeCatalog
        else if (section === "users")         cat = root.userCatalog
        else if (section === "parties")       cat = root.partyCatalog
        else if (section === "documents")     cat = root.documentCatalog
        else if (section === "structures")    cat = root.documentStructureCatalog
        if (!cat) return null
        const items = cat.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(rowId)) return items[i]
        }
        return null
    }

    readonly property var _orgColumns: [
        { key: "title",       label: "Name",             flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Timezone",  flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",           flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Version",          flex: 1, minWidth: 80,  sortable: false, visible: true }
    ]
    readonly property var _siteColumns: [
        { key: "title",       label: "Name",              flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Location",   flex: 4, minWidth: 200, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",            flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Timezone / FX",     flex: 2, minWidth: 150, sortable: false, visible: true }
    ]
    readonly property var _deptColumns: [
        { key: "title",       label: "Name",            flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type",     flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",          flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Cost Center",     flex: 2, minWidth: 120, sortable: false, visible: true }
    ]
    readonly property var _employeeColumns: [
        { key: "title",       label: "Name",                 flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Job Title",     flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",               flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Employment",           flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
    readonly property var _userColumns: [
        { key: "title",       label: "Display Name",   flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Username",        flex: 3, minWidth: 180, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",          flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Security",        flex: 3, minWidth: 180, sortable: false, visible: true }
    ]
    readonly property var _partyColumns: [
        { key: "title",       label: "Name",           flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type",    flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",         flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Legal Name",     flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
    readonly property var _documentColumns: [
        { key: "title",       label: "Title",          flex: 3, minWidth: 180, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type",    flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",         flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Storage",        flex: 3, minWidth: 160, sortable: false, visible: true }
    ]
    readonly property var _moduleColumns: [
        { key: "title",       label: "Module",          flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Stage / License", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Lifecycle",       flex: 0, minWidth: 100, sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Runtime",         flex: 3, minWidth: 200, sortable: false, visible: true }
    ]
    readonly property var _structureColumns: [
        { key: "title",       label: "Name",           flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Code / Type",    flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",         flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Info",           flex: 2, minWidth: 120, sortable: false, visible: true }
    ]

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy        : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading     : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage  : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    // ── Helper functions ──────────────────────────────────────────
    function catalogItemById(catalog, itemId) {
        const items = catalog.items || []
        for (let i = 0; i < items.length; i++) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openOrganizationEdit(itemId) {
        const item = root.catalogItemById(root.organizationCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openOrganizationEdit", item.state || {})
    }

    function openEntityDetail(sectionId, itemId) {
        root._activeSection = String(sectionId || root._activeSection || "")
        root._selectedRowId = String(itemId || "")
        if (root._activeSection === "documents" && root._selectedRowId.length > 0) {
            root.inspectDocument(root._selectedRowId)
        }
        root._entityDetailOpen = root._selectedRowId.length > 0
    }

    function openAdminEntitySection(sectionId, rowId) {
        root._activeSection = String(sectionId || "")
        root._selectedRowId = rowId ? String(rowId) : ""
        if (root._activeSection === "documents" && root._selectedRowId.length > 0) {
            root.inspectDocument(root._selectedRowId)
        }
        root._entityDetailOpen = root._selectedRowId.length > 0
    }

    function closeEntityDetail() {
        root._entityDetailOpen = false
    }

    function handleEntityDetailAction(sectionId, actionId) {
        const id = root._selectedRowId
        if (actionId === "create_department") {
            dialogHostLoader.invoke("openDepartmentCreate")
            return
        }
        if (actionId === "create_employee") {
            dialogHostLoader.invoke("openEmployeeCreate")
            return
        }
        if (actionId === "show_departments") {
            root.openAdminEntitySection("departments", "")
            return
        }
        if (actionId === "show_employees") {
            root.openAdminEntitySection("employees", "")
            return
        }
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
            if      (sectionId === "sites")      root.openSiteEdit(id)
            else if (sectionId === "departments") root.openDepartmentEdit(id)
            else if (sectionId === "employees")   root.openEmployeeEdit(id)
            else if (sectionId === "users")       root.openUserEdit(id)
            else if (sectionId === "parties")     root.openPartyEdit(id)
            else if (sectionId === "documents")   root.openDocumentEdit(id)
            else if (sectionId === "structures")  root.openDocumentStructureEdit(id)
            return
        }
        if (actionId === "toggle_active" && root.workspaceController) {
            if      (sectionId === "sites")       root.workspaceController.toggleSiteActive(id)
            else if (sectionId === "departments") root.workspaceController.toggleDepartmentActive(id)
            else if (sectionId === "employees")   root.workspaceController.toggleEmployeeActive(id)
            else if (sectionId === "users")       root.workspaceController.toggleUserActive(id)
            else if (sectionId === "parties")     root.workspaceController.togglePartyActive(id)
            else if (sectionId === "documents")   root.workspaceController.toggleDocumentActive(id)
            else if (sectionId === "structures")  root.workspaceController.toggleDocumentStructureActive(id)
        }
    }

    function openSiteEdit(itemId) {
        const item = root.catalogItemById(root.siteCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openSiteEdit", item.state || {})
    }

    function openDepartmentEdit(itemId) {
        const item = root.catalogItemById(root.departmentCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openDepartmentEdit", item.state || {})
    }

    function openEmployeeEdit(itemId) {
        const item = root.catalogItemById(root.employeeCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openEmployeeEdit", item.state || {})
    }

    function openUserEdit(itemId) {
        const item = root.catalogItemById(root.userCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openUserEdit", item.state || {})
    }

    function openPartyEdit(itemId) {
        const item = root.catalogItemById(root.partyCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openPartyEdit", item.state || {})
    }

    function inspectDocument(itemId) {
        if (root.workspaceController !== null) root.workspaceController.selectDocument(itemId)
    }

    function openDocumentEdit(itemId) {
        const item = root.catalogItemById(root.documentCatalog, itemId)
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
        const item = root.catalogItemById(root.documentStructureCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openDocumentStructureEdit", item.state || {})
    }

    title: root.workspaceController
        ? (root.workspaceController.overview.title || root.workspaceModel.title)
        : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // ── Shell layout ──────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── Left navigation sidebar ───────────────────────────────
            AdminNavSidebar {
                id: _sidebar
                Layout.fillHeight:     true
                Layout.preferredWidth: implicitWidth
                activeSection: root._activeSection
                onSectionChanged: function(section) {
                    root._activeSection = section
                    root._entityDetailOpen = false
                    root._selectedRowId = ""
                }
            }

        // ── Center workspace ──────────────────────────────────────
        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            // ── Organizations ─────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "organizations" && !root._detailOpen
                sectionTitle:    "Organizations"
                entityLabel:     "Organization"
                catalog:         root.organizationCatalog
                catalogModel:    root.organizationsTableModel
                columns:         root._orgColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openOrganizationCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("organizations", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            Loader {
                id: organizationDetailLoader
                anchors.fill: parent
                active: root._activeSection === "organizations" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminOrganizationDetailPage {
                        organization: root._detailItem || ({})
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok

                        onBackRequested: root.closeEntityDetail()

                        onActionRequested: function(actionId) {
                            if (actionId === "edit") {
                                root.openOrganizationEdit(root._selectedRowId)
                            } else if (actionId === "set_active") {
                                if (root.workspaceController)
                                    root.workspaceController.setActiveOrganization(root._selectedRowId)
                            } else if (actionId === "refresh") {
                                if (root.workspaceController)
                                    root.workspaceController.refresh()
                            } else if (actionId === "show_audit") {
                                root.openAdminEntitySection("audit", "")
                            }
                        }
                    }
                }
            }

            // ── Sites ─────────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "sites" && !root._detailOpen
                sectionTitle:    "Sites"
                entityLabel:     "Site"
                catalog:         root.siteCatalog
                catalogModel:    root.sitesTableModel
                columns:         root._siteColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openSiteCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("sites", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Departments ───────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "departments" && !root._detailOpen
                sectionTitle:    "Departments"
                entityLabel:     "Department"
                catalog:         root.departmentCatalog
                catalogModel:    root.departmentsTableModel
                columns:         root._deptColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openDepartmentCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("departments", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Employees ─────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "employees" && !root._detailOpen
                sectionTitle:    "Employees"
                entityLabel:     "Employee"
                catalog:         root.employeeCatalog
                catalogModel:    root.employeesTableModel
                columns:         root._employeeColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openEmployeeCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("employees", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Users ─────────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "users" && !root._detailOpen
                sectionTitle:    "Users"
                entityLabel:     "User"
                catalog:         root.userCatalog
                catalogModel:    root.usersTableModel
                columns:         root._userColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openUserCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("users", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Parties ───────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "parties" && !root._detailOpen
                sectionTitle:    "Parties"
                entityLabel:     "Party"
                catalog:         root.partyCatalog
                catalogModel:    root.partiesTableModel
                columns:         root._partyColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openPartyCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("parties", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Documents ─────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "documents" && !root._detailOpen
                sectionTitle:    "Documents"
                entityLabel:     "Document"
                catalog:         root.documentCatalog
                catalogModel:    root.documentsTableModel
                columns:         root._documentColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openDocumentCreate")
                onRowSelected:      function(id) {
                    root._selectedRowId = id
                    root.inspectDocument(id)
                }
                onRowActivated:     function(id) { root.openEntityDetail("documents", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Document Structures ───────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "structures" && !root._detailOpen
                sectionTitle:    "Document Structures"
                entityLabel:     "Structure"
                catalog:         root.documentStructureCatalog
                catalogModel:    root.documentStructuresTableModel
                columns:         root._structureColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openDocumentStructureCreate")
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("structures", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            Loader {
                id: siteDetailLoader
                anchors.fill: parent
                active: root._activeSection === "sites" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminSiteDetailPage {
                        platformCatalog: root.platformCatalog
                        site: root._detailItem || ({})
                        departmentCatalog: root.departmentCatalog
                        departmentColumns: root._deptColumns
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("sites", actionId)
                        }
                        onRelatedRowActivated: function(sectionId, rowId) {
                            root.openAdminEntitySection(sectionId, rowId)
                        }
                    }
                }
            }

            Loader {
                id: departmentDetailLoader
                anchors.fill: parent
                active: root._activeSection === "departments" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminDepartmentDetailPage {
                        platformCatalog: root.platformCatalog
                        department: root._detailItem || ({})
                        employeeCatalog: root.employeeCatalog
                        employeeColumns: root._employeeColumns
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("departments", actionId)
                        }
                        onRelatedRowActivated: function(sectionId, rowId) {
                            root.openAdminEntitySection(sectionId, rowId)
                        }
                    }
                }
            }

            Loader {
                id: employeeDetailLoader
                anchors.fill: parent
                active: root._activeSection === "employees" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminEmployeeDetailPage {
                        employee: root._detailItem || ({})
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("employees", actionId)
                        }
                    }
                }
            }

            Loader {
                id: userDetailLoader
                anchors.fill: parent
                active: root._activeSection === "users" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminUserDetailPage {
                        user: root._detailItem || ({})
                        moduleEntitlementCatalog: root.moduleEntitlementCatalog
                        moduleEntitlementColumns: root._moduleColumns
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("users", actionId)
                        }
                    }
                }
            }

            Loader {
                id: partyDetailLoader
                anchors.fill: parent
                active: root._activeSection === "parties" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminPartyDetailPage {
                        party: root._detailItem || ({})
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("parties", actionId)
                        }
                    }
                }
            }

            Loader {
                id: documentDetailLoader
                anchors.fill: parent
                active: root._activeSection === "documents" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminDocumentsDetailPage {
                        document: root._detailItem || ({})
                        selectedDocument: root.selectedDocument
                        documentPreviewState: root.documentPreviewState
                        documentLinkCatalog: root.documentLinkCatalog
                        workspaceController: root.workspaceController
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
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
                active: root._activeSection === "structures" && root._detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    AdminDocumentStructureDetailPage {
                        structure: root._detailItem || ({})
                        busy: root._busy
                        errorMessage: root._err
                        feedbackMessage: root._ok
                        onBackRequested: root.closeEntityDetail()
                        onActionRequested: function(actionId) {
                            root.handleEntityDetailAction("structures", actionId)
                        }
                    }
                }
            }

            // ── Roles & Access ────────────────────────────────────
            Item {
                anchors.fill: parent
                visible:      root._activeSection === "access"

                PlatformWidgets.AccessSecurityPanel {
                    anchors.fill: parent
                    visible:      !root._accessDetailOpen
                    controller:   root.accessController
                    onGrantActivated: function(grantId) {
                        root._accessGrantId = grantId
                        root._accessDetailOpen = true
                    }
                }

                Loader {
                    anchors.fill: parent
                    active:       root._activeSection === "access" && root._accessDetailOpen
                    visible:      active && status === Loader.Ready
                    asynchronous: true
                    sourceComponent: Component {
                        AdminAccessDetailPage {
                            controller:      root.accessController
                            grantId:         root._accessGrantId
                            busy:            root.accessController ? root.accessController.isBusy : false
                            errorMessage:    root.accessController ? root.accessController.errorMessage : ""
                            feedbackMessage: root.accessController ? root.accessController.feedbackMessage : ""
                            onBackRequested: root._accessDetailOpen = false
                        }
                    }
                }
            }

            // ── Support ───────────────────────────────────────────
            AdminSupportSection {
                anchors.fill:      parent
                visible:           root._activeSection === "support"
                supportController: root.supportController
            }

            // ── Audit / Overview ──────────────────────────────────
            AdminAuditSection {
                anchors.fill:        parent
                visible:             root._activeSection === "audit"
                workspaceController: root.workspaceController
            }
        }

        // ── Right detail panel ────────────────────────────────────
        Rectangle {
            id: _detailPanel
            Layout.fillHeight:     true
            Layout.preferredWidth: 288
            visible:               false
            color:                 Theme.AppTheme.surface
            z:                     1

            Rectangle {
                anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                width: 1; color: Theme.AppTheme.divider
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Panel header
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight : Theme.AppTheme.toolbarHeight - 6
                    color:  Theme.AppTheme.surfaceRaised

                    Rectangle {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }

                    AppControls.Label {
                        anchors.left:           parent.left
                        anchors.leftMargin:     Theme.AppTheme.marginMd
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right:          _closeBtn.left
                        anchors.rightMargin:    4
                        text:           root._detailItem ? (root._detailItem.title || "Details") : "Details"
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold:      true
                        elide:          Text.ElideRight
                    }

                    Rectangle {
                        id: _closeBtn
                        anchors.right:          parent.right
                        anchors.rightMargin:    6
                        anchors.verticalCenter: parent.verticalCenter
                        width: 26; height: 26; radius: 4
                        color: _closeMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                        AppIcons.AppIcon {
                            anchors.centerIn: parent
                            name: "close"; size: 10
                            iconColor: Theme.AppTheme.textMuted
                        }

                        MouseArea {
                            id: _closeMA
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape:  Qt.PointingHandCursor
                            onClicked:    root._selectedRowId = ""
                        }
                    }
                }

                // Panel body (scrollable)
                Flickable {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    contentWidth:      width
                    contentHeight:     _panelContent.implicitHeight
                    clip:              true
                    boundsBehavior:    Flickable.StopAtBounds

                    ColumnLayout {
                        id: _panelContent
                        width: parent.width
                        spacing: 0

                        // ── Document inspector ────────────────────────────
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root._activeSection === "documents"
                            spacing: 0

                            PlatformWidgets.DocumentDetailPanel {
                                Layout.fillWidth: true
                                details:         root.selectedDocument
                                previewState:    root.documentPreviewState
                                actionsEnabled:  root.workspaceController
                                    ? !root.workspaceController.isBusy : false
                                onOpenRequested: function(url) {
                                    if (url && url.length > 0) Qt.openUrlExternally(url)
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1; color: Theme.AppTheme.divider
                            }

                            // Document actions
                            RowLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.topMargin:    Theme.AppTheme.spacingSm
                                Layout.bottomMargin: Theme.AppTheme.spacingXs
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text:     "Edit"
                                    iconName: "edit"
                                    enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                    onClicked: root.openDocumentEdit(root._selectedRowId)
                                }

                                AppControls.SecondaryButton {
                                    text:     "Toggle"
                                    iconName: "approve"
                                    enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                    onClicked: {
                                        if (root.workspaceController)
                                            root.workspaceController.toggleDocumentActive(root._selectedRowId)
                                    }
                                }
                            }

                            AppControls.SecondaryButton {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.bottomMargin: Theme.AppTheme.spacingSm
                                text:     "Delete"
                                iconName: "delete"
                                danger:   true
                                enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                onClicked: { /* root.workspaceController.deleteDocument(root._selectedRowId) */ }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight : 1; color: Theme.AppTheme.divider
                            }

                            // Linked records header
                            RowLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.topMargin:    Theme.AppTheme.spacingSm
                                Layout.bottomMargin: Theme.AppTheme.spacingSm
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text:           "Linked Records"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }

                                AppControls.Label {
                                    visible: (root.documentLinkCatalog.items || []).length > 0
                                    text:    String((root.documentLinkCatalog.items || []).length)
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }

                                AppControls.SecondaryButton {
                                    text:     "Add Link"
                                    iconName: "add"
                                    enabled:  root.selectedDocument.hasSelection
                                        && (root.workspaceController ? !root.workspaceController.isBusy : false)
                                    onClicked: root.openDocumentLinkCreate()
                                }
                            }

                            Repeater {
                                model: root.documentLinkCatalog.items || []

                                delegate: Rectangle {
                                    id : delegateRoot
                                    required property var modelData
                                    required property int index

                                    width:  _panelContent.width
                                    height: 34
                                    color:  _linkRowMA.containsMouse
                                        ? Theme.AppTheme.hoverSurface : "transparent"

                                    Rectangle {
                                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                        height: 1; color: Theme.AppTheme.divider
                                    }

                                    RowLayout {
                                        anchors.fill:        parent
                                        anchors.leftMargin:  Theme.AppTheme.marginMd
                                        anchors.rightMargin: Theme.AppTheme.marginSm
                                        spacing: Theme.AppTheme.spacingXs

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text:           delegateRoot.modelData.title || ""
                                            color:          Theme.AppTheme.textPrimary
                                            font.family:    Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            elide:          Text.ElideRight
                                        }

                                        Rectangle {
                                            Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: 4
                                            color: _removeLinkMA.containsMouse
                                                ? Theme.AppTheme.dangerSoft : "transparent"

                                            AppIcons.AppIcon {
                                                anchors.centerIn: parent
                                                name: "close"; size: 9
                                                iconColor: _removeLinkMA.containsMouse
                                                    ? Theme.AppTheme.danger
                                                    : Theme.AppTheme.textMuted
                                            }

                                            MouseArea {
                                                id: _removeLinkMA
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape:  Qt.PointingHandCursor
                                                enabled:      root.workspaceController
                                                    ? !root.workspaceController.isBusy : false
                                                onClicked: {
                                                    if (root.workspaceController)
                                                        root.workspaceController.removeDocumentLink(modelData.id)
                                                }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: _linkRowMA
                                        anchors.fill: parent
                                        hoverEnabled: true
                                    }
                                }
                            }
                        }

                        // ── Generic entity inspector ──────────────────────
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.margins:   Theme.AppTheme.marginMd
                            visible:          root._activeSection !== "documents"
                            spacing:          Theme.AppTheme.spacingSm

                            // Entity name
                            AppControls.Label {
                                Layout.fillWidth: true
                                text:           root._detailItem ? (root._detailItem.title || "") : ""
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold:      true
                                wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                            }

                            // Status chip
                            AppWidgets.StatusChip {
                                visible: root._detailItem
                                    ? (root._detailItem.statusLabel || "").length > 0 : false
                                status: root._detailItem ? (root._detailItem.statusLabel || "") : ""
                            }

                            // Divider
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: 2; Layout.bottomMargin: 2
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // Details field
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root._detailItem
                                    ? (root._detailItem.subtitle || "").length > 0 : false

                                AppControls.Label {
                                    text:           "Details"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text:           root._detailItem ? (root._detailItem.subtitle || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Info field
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root._detailItem
                                    ? (root._detailItem.metaText || "").length > 0 : false

                                AppControls.Label {
                                    text:           "Info"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text:           root._detailItem ? (root._detailItem.metaText || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Action divider
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: 2
                                height: 1; color: Theme.AppTheme.divider
                                visible: root._detailItem !== null
                            }

                            // Primary actions: Edit + Set Active / Toggle
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs
                                visible: root._detailItem !== null

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text:     "Edit"
                                    iconName: "edit"
                                    enabled:  !root._busy
                                    onClicked: {
                                        const id = root._selectedRowId
                                        const s  = root._activeSection
                                        if      (s === "organizations") root.openOrganizationEdit(id)
                                        else if (s === "sites")         root.openSiteEdit(id)
                                        else if (s === "departments")   root.openDepartmentEdit(id)
                                        else if (s === "employees")     root.openEmployeeEdit(id)
                                        else if (s === "users")         root.openUserEdit(id)
                                        else if (s === "parties")       root.openPartyEdit(id)
                                        else if (s === "structures")    root.openDocumentStructureEdit(id)
                                    }
                                }

                                AppControls.SecondaryButton {
                                    visible:  root._activeSection === "organizations"
                                    text:     "Set Active"
                                    iconName: "approve"
                                    enabled:  !root._busy
                                    onClicked: {
                                        if (root.workspaceController)
                                            root.workspaceController.setActiveOrganization(root._selectedRowId)
                                    }
                                }

                                AppControls.SecondaryButton {
                                    visible:  root._activeSection !== "organizations"
                                    text:     "Toggle"
                                    iconName: "approve"
                                    enabled:  !root._busy
                                    onClicked: {
                                        const id = root._selectedRowId
                                        const s  = root._activeSection
                                        if (!root.workspaceController) return
                                        if      (s === "sites")       root.workspaceController.toggleSiteActive(id)
                                        else if (s === "departments") root.workspaceController.toggleDepartmentActive(id)
                                        else if (s === "employees")   root.workspaceController.toggleEmployeeActive(id)
                                        else if (s === "users")       root.workspaceController.toggleUserActive(id)
                                        else if (s === "parties")     root.workspaceController.togglePartyActive(id)
                                        else if (s === "structures")  root.workspaceController.toggleDocumentStructureActive(id)
                                    }
                                }
                            }

                            // Delete action
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                visible:  root._detailItem !== null
                                text:     "Delete"
                                iconName: "delete"
                                danger:   true
                                enabled:  !root._busy
                                onClicked: { /* root.workspaceController.deleteEntity(root._selectedRowId) */ }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Dialog host ───────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            AdminDialogHost {
                workspaceController: root.workspaceController
            }
        }
    }
}
