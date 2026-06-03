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
import "components" as Components
import "detail" as Detail
import "panels" as Panels
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
    property var organizationCatalog: root.workspaceController
        ? root.workspaceController.organizations
        : ({ "title": "Organizations", "subtitle": "", "emptyState": "", "items": [] })
    property var calendarCatalog: root.workspaceController
        ? root.workspaceController.calendars
        : ({ "title": "Calendars", "subtitle": "", "emptyState": "", "items": [] })
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

    // -- Python-owned table models ---------------------------------
    property var organizationsTableModel:     root.workspaceController ? root.workspaceController.organizationsTableModel     : null
    property var calendarsTableModel:         root.workspaceController ? root.workspaceController.calendarsTableModel         : null
    property var sitesTableModel:             root.workspaceController ? root.workspaceController.sitesTableModel             : null
    property var departmentsTableModel:       root.workspaceController ? root.workspaceController.departmentsTableModel       : null
    property var employeesTableModel:         root.workspaceController ? root.workspaceController.employeesTableModel         : null
    property var usersTableModel:             root.workspaceController ? root.workspaceController.usersTableModel             : null
    property var partiesTableModel:           root.workspaceController ? root.workspaceController.partiesTableModel           : null
    property var documentsTableModel:         root.workspaceController ? root.workspaceController.documentsTableModel         : null
    property var documentStructuresTableModel:root.workspaceController ? root.workspaceController.documentStructuresTableModel : null

    // -- Navigation & selection state ------------------------------
    property string _activeSection: "organizations"
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
        if      (section === "organizations") cat = root.organizationCatalog
        else if (section === "calendars")     cat = root.calendarCatalog
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




    function openOrganizationEdit(itemId) {
        const item = adminState.catalogItemById(root.organizationCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openOrganizationEdit", item.state || {})
    }

    function openCalendarEdit(itemId) {
        const item = adminState.catalogItemById(root.calendarCatalog, itemId)
        if (item !== null) {
            const state = item.state || {}
            if (state.isEnterpriseCalendar === true)
                dialogHostLoader.invoke("openCalendarEdit", state)
            else
                dialogHostLoader.invoke("openWorkingCalendarEdit", state)
        }
    }

    function openEntityDetail(sectionId, itemId) {
        adminState.activeSection = String(sectionId || adminState.activeSection || "")
        adminState.selectedRowId = String(itemId || "")
        if (adminState.activeSection === "documents" && adminState.selectedRowId.length > 0) {
            root.inspectDocument(adminState.selectedRowId)
        }
        adminState.entityDetailOpen = adminState.selectedRowId.length > 0
    }

    function openAdminEntitySection(sectionId, rowId) {
        adminState.activeSection = String(sectionId || "")
        adminState.selectedRowId = rowId ? String(rowId) : ""
        if (adminState.activeSection === "documents" && adminState.selectedRowId.length > 0) {
            root.inspectDocument(adminState.selectedRowId)
        }
        adminState.entityDetailOpen = adminState.selectedRowId.length > 0
    }

    function closeEntityDetail() {
        adminState.entityDetailOpen = false
    }

    function _calendarEntityType(sectionId) {
        if (sectionId === "sites")
            return "site"
        if (sectionId === "departments")
            return "department"
        if (sectionId === "employees")
            return "employee"
        return ""
    }

    function _calendarOptions() {
        const rows = root.calendarCatalog.items || []
        const options = []
        for (let i = 0; i < rows.length; i++) {
            const item = rows[i] || {}
            const state = item.state || {}
            const id = String(state.calendarId || state.id || item.id || "")
            if (!id.length)
                continue
            options.push({
                "id": id,
                "name": String(state.name || item.title || id),
                "code": String(state.code || ""),
                "calendarType": String(state.calendarType || item.statusLabel || "")
            })
        }
        return options
    }

    function _calendarEntityId(sectionId, item) {
        const state = item && item.state ? item.state : {}
        if (sectionId === "sites")
            return String(state.siteId || state.id || item.id || "")
        if (sectionId === "departments")
            return String(state.departmentId || state.id || item.id || "")
        if (sectionId === "employees")
            return String(state.employeeId || state.id || item.id || "")
        return ""
    }

    function _calendarAssignmentContext(sectionId, item, refreshKey) {
        if (!root.workspaceController || !item)
            return ({ "assignedCalendar": {}, "sourceChain": [] })
        const state = item.state || {}
        const entityType = root._calendarEntityType(sectionId)
        const entityId = root._calendarEntityId(sectionId, item)
        if (!entityType.length || !entityId.length)
            return ({ "assignedCalendar": {}, "sourceChain": [] })
        return root.workspaceController.calendarAssignmentContext(
            entityType,
            entityId,
            String(state.siteId || ""),
            String(state.departmentId || "")
        )
    }

    function _calendarDetailContext(item, refreshKey) {
        if (!root.workspaceController || !item)
            return ({ "workingRules": [], "exceptions": [], "recurringEvents": [], "assignments": {} })
        const state = item.state || {}
        const calendarId = String(state.calendarId || state.id || item.id || "")
        if (!calendarId.length)
            return ({ "workingRules": [], "exceptions": [], "recurringEvents": [], "assignments": {} })
        return root.workspaceController.calendarDetailContext(calendarId)
    }

    function handleEntityDetailAction(sectionId, actionId) {
        const id = adminState.selectedRowId
        if (actionId === "assign_calendar") {
            const entityType = root._calendarEntityType(sectionId)
            const item = root._detailItem || {}
            const entityId = root._calendarEntityId(sectionId, item)
            if (entityType.length && entityId.length) {
                dialogHostLoader.invoke(
                    "openCalendarAssign",
                    entityType,
                    entityId,
                    String(item.title || entityId),
                    root._calendarOptions()
                )
            }
            return
        }
        if (actionId === "clear_calendar_assignment") {
            const entityType = root._calendarEntityType(sectionId)
            const ctx = root._calendarAssignmentContext(sectionId, root._detailItem, root.calendarCatalog)
            const assigned = ctx.assignedCalendar || {}
            const assignmentId = String(assigned.assignmentId || "")
            if (root.workspaceController && entityType.length && assignmentId.length) {
                root.workspaceController.removeCalendarAssignment(assignmentId, entityType)
            }
            return
        }
        if (actionId === "open_calendar_mgmt") {
            root.openAdminEntitySection("calendars", "")
            return
        }
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
        const item = adminState.catalogItemById(root.siteCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openSiteEdit", item.state || {})
    }

    function openDepartmentEdit(itemId) {
        const item = adminState.catalogItemById(root.departmentCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openDepartmentEdit", item.state || {})
    }

    function openEmployeeEdit(itemId) {
        const item = adminState.catalogItemById(root.employeeCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openEmployeeEdit", item.state || {})
    }

    function openUserEdit(itemId) {
        const item = adminState.catalogItemById(root.userCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openUserEdit", item.state || {})
    }

    function openPartyEdit(itemId) {
        const item = adminState.catalogItemById(root.partyCatalog, itemId)
        if (item !== null) dialogHostLoader.invoke("openPartyEdit", item.state || {})
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
            Components.AdminNavSidebar {
                id: _sidebar
                Layout.fillHeight:     true
                Layout.preferredWidth: implicitWidth
                activeSection: adminState.activeSection
                onSectionChanged: function(section) {
                    adminState.activeSection = section
                    adminState.entityDetailOpen = false
                    adminState.selectedRowId = ""
                }
            }

        // -- Center workspace --------------------------------------
        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            // -- Organizations -------------------------------------
            Components.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "organizations" && !adminState.detailOpen
                sectionTitle:    "Organizations"
                entityLabel:     "Organization"
                catalog:         root.organizationCatalog
                catalogModel:    root.organizationsTableModel
                columns:         adminState.orgColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openOrganizationCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("organizations", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            Loader {
                id: organizationDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "organizations" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminOrganizationDetailPage {
                        organization: root._detailItem || ({})
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok

                        onBackRequested: root.closeEntityDetail()

                        onActionRequested: function(actionId) {
                            if (actionId === "edit") {
                                root.openOrganizationEdit(adminState.selectedRowId)
                            } else if (actionId === "set_active") {
                                if (root.workspaceController)
                                    root.workspaceController.setActiveOrganization(adminState.selectedRowId)
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

            // -- Sites ---------------------------------------------
            Components.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "calendars" && !adminState.detailOpen
                sectionTitle:    "Calendars"
                entityLabel:     "Calendar"
                catalog:         root.calendarCatalog
                catalogModel:    root.calendarsTableModel
                columns:         adminState.calendarColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openCalendarCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("calendars", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            Loader {
                id: calendarDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "calendars" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminCalendarDetailPage {
                        property var _calendarContext: root._calendarDetailContext(root._detailItem, root.calendarCatalog)
                        property var _calendarState: root._detailItem && root._detailItem.state ? root._detailItem.state : ({})
                        property string _calendarId: String(_calendarState.calendarId || _calendarState.id || (root._detailItem ? root._detailItem.id : "") || "")

                        workspaceController: root.workspaceController
                        calendar: root._detailItem || ({})
                        workingRules: _calendarContext.workingRules || []
                        enterpriseExceptions: _calendarContext.exceptions || []
                        recurringEvents: _calendarContext.recurringEvents || []
                        assignments: _calendarContext.assignments || ({})
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
                        isEnterpriseCalendar: _calendarState.isEnterpriseCalendar === true
                        onBackRequested: root.closeEntityDetail()
                        onEditRequested: root.openCalendarEdit(adminState.selectedRowId)
                        onAddHolidayRequested: {
                            if (_calendarState.isEnterpriseCalendar === true && _calendarId.length > 0)
                                dialogHostLoader.invoke("openCalendarExceptionCreate", _calendarId)
                            else
                                dialogHostLoader.invoke("openWorkingCalendarHolidayCreate")
                        }
                        onAddExceptionRequested: dialogHostLoader.invoke("openCalendarExceptionCreate", _calendarId)
                        onAddRecurringEventRequested: dialogHostLoader.invoke("openCalendarRecurringEventCreate", _calendarId)
                        onOpenAuditRequested: root.openAdminEntitySection("audit", "")
                    }
                }
            }

            Components.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "sites" && !adminState.detailOpen
                sectionTitle:    "Sites"
                entityLabel:     "Site"
                catalog:         root.siteCatalog
                catalogModel:    root.sitesTableModel
                columns:         adminState.siteColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openSiteCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("sites", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // -- Departments ---------------------------------------
            Components.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "departments" && !adminState.detailOpen
                sectionTitle:    "Departments"
                entityLabel:     "Department"
                catalog:         root.departmentCatalog
                catalogModel:    root.departmentsTableModel
                columns:         adminState.deptColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openDepartmentCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("departments", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // -- Employees -----------------------------------------
            Components.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "employees" && !adminState.detailOpen
                sectionTitle:    "Employees"
                entityLabel:     "Employee"
                catalog:         root.employeeCatalog
                catalogModel:    root.employeesTableModel
                columns:         adminState.employeeColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openEmployeeCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("employees", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // -- Users ---------------------------------------------
            Components.AdminEntityWorkspace {
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

            // -- Parties -------------------------------------------
            Components.AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         adminState.activeSection === "parties" && !adminState.detailOpen
                sectionTitle:    "Parties"
                entityLabel:     "Party"
                catalog:         root.partyCatalog
                catalogModel:    root.partiesTableModel
                columns:         adminState.partyColumns
                isBusy:          adminState.busy
                isLoading:       adminState.load
                errorMessage:    adminState.err
                feedbackMessage: adminState.ok
                selectedRowId:   adminState.selectedRowId

                onCreateRequested:  dialogHostLoader.invoke("openPartyCreate")
                onRowSelected:      function(id) { adminState.selectedRowId = id }
                onRowActivated:     function(id) { root.openEntityDetail("parties", id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // -- Documents -----------------------------------------
            Components.AdminEntityWorkspace {
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
            Components.AdminEntityWorkspace {
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
                id: siteDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "sites" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminSiteDetailPage {
                        property var _calendarContext: root._calendarAssignmentContext("sites", root._detailItem, root.calendarCatalog)

                        platformCatalog: root.platformCatalog
                        site: root._detailItem || ({})
                        departmentCatalog: root.departmentCatalog
                        departmentColumns: adminState.deptColumns
                        siteCalendarAssignment: _calendarContext.assignedCalendar || ({})
                        calendarSourceChain: _calendarContext.sourceChain || []
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
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
                active: adminState.activeSection === "departments" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminDepartmentDetailPage {
                        property var _calendarContext: root._calendarAssignmentContext("departments", root._detailItem, root.calendarCatalog)

                        platformCatalog: root.platformCatalog
                        department: root._detailItem || ({})
                        employeeCatalog: root.employeeCatalog
                        employeeColumns: adminState.employeeColumns
                        deptCalendarAssignment: _calendarContext.assignedCalendar || ({})
                        calendarSourceChain: _calendarContext.sourceChain || []
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
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
                active: adminState.activeSection === "employees" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminEmployeeDetailPage {
                        property var _calendarContext: root._calendarAssignmentContext("employees", root._detailItem, root.calendarCatalog)

                        employee: root._detailItem || ({})
                        pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
                        empCalendarAssignment: _calendarContext.assignedCalendar || ({})
                        calendarSourceChain: _calendarContext.sourceChain || []
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
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
                active: adminState.activeSection === "users" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminUserDetailPage {
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
                id: partyDetailLoader
                anchors.fill: parent
                active: adminState.activeSection === "parties" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminPartyDetailPage {
                        party: root._detailItem || ({})
                        inventoryEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("inventory_procurement") : false
                        pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
                        busy: adminState.busy
                        errorMessage: adminState.err
                        feedbackMessage: adminState.ok
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
                active: adminState.activeSection === "documents" && adminState.detailOpen
                visible: active
                asynchronous: true

                sourceComponent: Component {
                    Detail.AdminDocumentsDetailPage {
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
                    Detail.AdminDocumentStructureDetailPage {
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

                PlatformWidgets.AccessSecurityPanel {
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
                        Detail.AdminAccessDetailPage {
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
            Sections.AdminSupportSection {
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


        // -- Right detail panel ------------------------------------
        Panels.AdminEntityDetailPanel {
            id: _detailPanel
            Layout.fillHeight:     true
            Layout.preferredWidth: 288
            visible:               false
            activeSection:   adminState.activeSection
            detailItem:      root._detailItem
            selectedRowId:   adminState.selectedRowId
            selectedDocument:      root.selectedDocument
            documentPreviewState:  root.documentPreviewState
            documentLinkCatalog:   root.documentLinkCatalog
            workspaceController:   root.workspaceController
            busy:            adminState.busy
            onCloseRequested:                adminState.selectedRowId = ""
            onEditRequested: function(sectionId, itemId) {
                if      (sectionId === "organizations") root.openOrganizationEdit(itemId)
                else if (sectionId === "calendars")     root.openCalendarEdit(itemId)
                else if (sectionId === "sites")         root.openSiteEdit(itemId)
                else if (sectionId === "departments")   root.openDepartmentEdit(itemId)
                else if (sectionId === "employees")     root.openEmployeeEdit(itemId)
                else if (sectionId === "users")         root.openUserEdit(itemId)
                else if (sectionId === "parties")       root.openPartyEdit(itemId)
                else if (sectionId === "structures")    root.openDocumentStructureEdit(itemId)
            }
            onSetActiveOrganizationRequested: function(itemId) {
                if (root.workspaceController) root.workspaceController.setActiveOrganization(itemId)
            }
            onToggleEntityRequested: function(sectionId, itemId) {
                if (!root.workspaceController) return
                if      (sectionId === "sites")       root.workspaceController.toggleSiteActive(itemId)
                else if (sectionId === "departments") root.workspaceController.toggleDepartmentActive(itemId)
                else if (sectionId === "employees")   root.workspaceController.toggleEmployeeActive(itemId)
                else if (sectionId === "users")       root.workspaceController.toggleUserActive(itemId)
                else if (sectionId === "parties")     root.workspaceController.togglePartyActive(itemId)
                else if (sectionId === "structures")  root.workspaceController.toggleDocumentStructureActive(itemId)
            }
            onDocumentLinkCreateRequested: root.openDocumentLinkCreate()
            onDocumentEditRequested: function(itemId) { root.openDocumentEdit(itemId) }
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
