import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog: platformWorkspaceCatalog
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
    property var organizationCatalog: workspaceController
        ? workspaceController.organizations
        : ({
            "title": "Organizations",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var siteCatalog: workspaceController
        ? workspaceController.sites
        : ({
            "title": "Sites",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var departmentCatalog: workspaceController
        ? workspaceController.departments
        : ({
            "title": "Departments",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var employeeCatalog: workspaceController
        ? workspaceController.employees
        : ({
            "title": "Employees",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var userCatalog: workspaceController
        ? workspaceController.users
        : ({
            "title": "Users",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var partyCatalog: workspaceController
        ? workspaceController.parties
        : ({
            "title": "Parties",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var documentCatalog: workspaceController
        ? workspaceController.documents
        : ({
            "title": "Documents",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var selectedDocument: workspaceController
        ? workspaceController.selectedDocument
        : ({
            "hasSelection": false,
            "documentId": "",
            "title": "Select a document",
            "summary": "",
            "badges": [],
            "metadataRows": [],
            "notes": ""
        })
    property var documentPreviewState: workspaceController
        ? workspaceController.documentPreview
        : ({
            "statusLabel": "No document selected",
            "summary": "",
            "canOpen": false,
            "openLabel": "Open Source",
            "openTargetUrl": ""
        })
    property var documentLinkCatalog: workspaceController
        ? workspaceController.documentLinks
        : ({
            "title": "Linked Records",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var documentStructureCatalog: workspaceController
        ? workspaceController.documentStructures
        : ({
            "title": "Document Structures",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })

    function catalogItemById(catalog, itemId) {
        const items = catalog.items || []
        for (let index = 0; index < items.length; index += 1) {
            if (items[index].id === itemId) {
                return items[index]
            }
        }
        return null
    }

    function openOrganizationCreate() {
        if (workspaceController === null) {
            return
        }
        organizationDialog.openForCreate(
            workspaceController.organizationEditorOptions.moduleOptions || []
        )
    }

    function openOrganizationEdit(itemId) {
        const item = catalogItemById(organizationCatalog, itemId)
        if (item === null) {
            return
        }
        organizationDialog.openForEdit(item.state || {})
    }

    function openSiteCreate() {
        if (workspaceController === null) {
            return
        }
        siteDialog.openForCreate()
    }

    function openSiteEdit(itemId) {
        const item = catalogItemById(siteCatalog, itemId)
        if (item === null) {
            return
        }
        siteDialog.openForEdit(item.state || {})
    }

    function openDepartmentCreate() {
        if (workspaceController === null) {
            return
        }
        departmentDialog.openForCreate(workspaceController.departmentEditorOptions || {})
    }

    function openDepartmentEdit(itemId) {
        const item = catalogItemById(departmentCatalog, itemId)
        if (item === null) {
            return
        }
        departmentDialog.openForEdit(item.state || {}, workspaceController.departmentEditorOptions || {})
    }

    function openEmployeeCreate() {
        if (workspaceController === null) {
            return
        }
        employeeDialog.openForCreate(workspaceController.employeeEditorOptions || {})
    }

    function openEmployeeEdit(itemId) {
        const item = catalogItemById(employeeCatalog, itemId)
        if (item === null) {
            return
        }
        employeeDialog.openForEdit(item.state || {}, workspaceController.employeeEditorOptions || {})
    }

    function openUserCreate() {
        if (workspaceController === null) {
            return
        }
        userDialog.openForCreate(workspaceController.userEditorOptions || {})
    }

    function openUserEdit(itemId) {
        const item = catalogItemById(userCatalog, itemId)
        if (item === null) {
            return
        }
        userDialog.openForEdit(item.state || {}, workspaceController.userEditorOptions || {})
    }

    function openPartyCreate() {
        if (workspaceController === null) {
            return
        }
        partyDialog.openForCreate(workspaceController.partyEditorOptions || {})
    }

    function openPartyEdit(itemId) {
        const item = catalogItemById(partyCatalog, itemId)
        if (item === null) {
            return
        }
        partyDialog.openForEdit(item.state || {}, workspaceController.partyEditorOptions || {})
    }

    function openDocumentCreate() {
        if (workspaceController === null) {
            return
        }
        documentDialog.openForCreate(workspaceController.documentEditorOptions || {})
    }

    function inspectDocument(itemId) {
        if (workspaceController === null) {
            return
        }
        workspaceController.selectDocument(itemId)
    }

    function openDocumentEdit(itemId) {
        const item = catalogItemById(documentCatalog, itemId)
        if (item === null) {
            return
        }
        inspectDocument(itemId)
        documentDialog.openForEdit(item.state || {}, workspaceController.documentEditorOptions || {})
    }

    function openDocumentStructureCreate() {
        if (workspaceController === null) {
            return
        }
        documentStructureDialog.openForCreate(workspaceController.documentStructureEditorOptions || {})
    }

    function openDocumentStructureEdit(itemId) {
        const item = catalogItemById(documentStructureCatalog, itemId)
        if (item === null || workspaceController === null) {
            return
        }
        documentStructureDialog.openForEdit(
            item.state || {},
            workspaceController.documentStructureEditorOptions || {}
        )
    }

    function openDocumentLinkCreate() {
        if (workspaceController === null || !selectedDocument.hasSelection) {
            return
        }
        documentLinkDialog.openForCreate(selectedDocument.documentId || "")
    }

    title: workspaceController ? (workspaceController.overview.title || workspaceModel.title) : workspaceModel.title
    subtitle: workspaceController ? workspaceController.overview.subtitle : ""

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            PlatformWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: workspaceController ? workspaceController.isLoading : false
                isBusy: workspaceController ? workspaceController.isBusy : false
                errorMessage: workspaceController ? workspaceController.errorMessage : ""
                feedbackMessage: workspaceController ? workspaceController.feedbackMessage : ""
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: workspaceController ? (workspaceController.overview.metrics || []) : []

                    delegate: AppWidgets.MetricCard {
                        required property var modelData

                        width: 210
                        label: modelData.label
                        value: modelData.value
                        supportingText: modelData.supportingText
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width > 1500 ? 3 : (width > 960 ? 2 : 1)
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingMd

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: organizationCatalog.title || "Organizations"
                    summary: organizationCatalog.subtitle || ""
                    catalog: organizationCatalog
                    createActionLabel: "New Organization"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Set Active"

                    onCreateRequested: openOrganizationCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openOrganizationEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.setActiveOrganization(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: siteCatalog.title || "Sites"
                    summary: siteCatalog.subtitle || ""
                    catalog: siteCatalog
                    createActionLabel: "New Site"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Toggle Active"

                    onCreateRequested: openSiteCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openSiteEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.toggleSiteActive(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: departmentCatalog.title || "Departments"
                    summary: departmentCatalog.subtitle || ""
                    catalog: departmentCatalog
                    createActionLabel: "New Department"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Toggle Active"

                    onCreateRequested: openDepartmentCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openDepartmentEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.toggleDepartmentActive(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: employeeCatalog.title || "Employees"
                    summary: employeeCatalog.subtitle || ""
                    catalog: employeeCatalog
                    createActionLabel: "New Employee"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Toggle Active"

                    onCreateRequested: openEmployeeCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openEmployeeEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.toggleEmployeeActive(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: userCatalog.title || "Users"
                    summary: userCatalog.subtitle || ""
                    catalog: userCatalog
                    createActionLabel: "New User"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Toggle Active"

                    onCreateRequested: openUserCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openUserEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.toggleUserActive(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: partyCatalog.title || "Parties"
                    summary: partyCatalog.subtitle || ""
                    catalog: partyCatalog
                    createActionLabel: "New Party"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Toggle Active"

                    onCreateRequested: openPartyCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openPartyEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.togglePartyActive(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: documentCatalog.title || "Documents"
                    summary: documentCatalog.subtitle || ""
                    catalog: documentCatalog
                    createActionLabel: "New Document"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Inspect"
                    secondaryActionLabel: "Edit"
                    tertiaryActionLabel: "Toggle Active"

                    onCreateRequested: openDocumentCreate()

                    onPrimaryActionRequested: function(itemId) {
                        inspectDocument(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        openDocumentEdit(itemId)
                    }

                    onTertiaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.toggleDocumentActive(itemId)
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width > 1480 ? 3 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingMd

                PlatformWidgets.DocumentDetailPanel {
                    Layout.fillWidth: true
                    Layout.columnSpan: width > 1480 ? 1 : 1
                    details: selectedDocument
                    previewState: documentPreviewState
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false

                    onOpenRequested: function(targetUrl) {
                        if (targetUrl && targetUrl.length > 0) {
                            Qt.openUrlExternally(targetUrl)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: documentLinkCatalog.title || "Linked Records"
                    summary: documentLinkCatalog.subtitle || ""
                    catalog: documentLinkCatalog
                    createActionLabel: "Add Link"
                    createEnabled: workspaceController
                        ? (!workspaceController.isBusy && selectedDocument.hasSelection)
                        : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    secondaryActionLabel: "Remove Link"
                    secondaryDanger: true

                    onCreateRequested: openDocumentLinkCreate()

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.removeDocumentLink(itemId)
                        }
                    }
                }

                PlatformWidgets.AdminCatalogPanel {
                    Layout.fillWidth: true
                    title: documentStructureCatalog.title || "Document Structures"
                    summary: documentStructureCatalog.subtitle || ""
                    catalog: documentStructureCatalog
                    createActionLabel: "New Structure"
                    createEnabled: workspaceController ? !workspaceController.isBusy : false
                    actionsEnabled: workspaceController ? !workspaceController.isBusy : false
                    primaryActionLabel: "Edit"
                    secondaryActionLabel: "Toggle Active"

                    onCreateRequested: openDocumentStructureCreate()

                    onPrimaryActionRequested: function(itemId) {
                        openDocumentStructureEdit(itemId)
                    }

                    onSecondaryActionRequested: function(itemId) {
                        if (workspaceController !== null) {
                            workspaceController.toggleDocumentStructureActive(itemId)
                        }
                    }
                }
            }

            PlatformWidgets.AccessSecurityPanel {
                Layout.fillWidth: true
                controller: accessController
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: workspaceController ? (workspaceController.overview.sections || []) : []

                    delegate: PlatformWidgets.OverviewSectionCard {
                        required property var modelData

                        width: 320
                        title: modelData.title
                        rows: modelData.rows
                        emptyState: modelData.emptyState
                    }
                }
            }
        }
    }

    PlatformDialogs.OrganizationEditorDialog {
        id: organizationDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createOrganization(payload)
                : workspaceController.updateOrganization(payload)
            if (result.ok) {
                organizationDialog.close()
            }
        }
    }

    PlatformDialogs.SiteEditorDialog {
        id: siteDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createSite(payload)
                : workspaceController.updateSite(payload)
            if (result.ok) {
                siteDialog.close()
            }
        }
    }

    PlatformDialogs.DepartmentEditorDialog {
        id: departmentDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createDepartment(payload)
                : workspaceController.updateDepartment(payload)
            if (result.ok) {
                departmentDialog.close()
            }
        }
    }

    PlatformDialogs.EmployeeEditorDialog {
        id: employeeDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createEmployee(payload)
                : workspaceController.updateEmployee(payload)
            if (result.ok) {
                employeeDialog.close()
            }
        }
    }

    PlatformDialogs.UserEditorDialog {
        id: userDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createUser(payload)
                : workspaceController.updateUser(payload)
            if (result.ok) {
                userDialog.close()
            }
        }
    }

    PlatformDialogs.PartyEditorDialog {
        id: partyDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createParty(payload)
                : workspaceController.updateParty(payload)
            if (result.ok) {
                partyDialog.close()
            }
        }
    }

    PlatformDialogs.DocumentEditorDialog {
        id: documentDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createDocument(payload)
                : workspaceController.updateDocument(payload)
            if (result.ok) {
                documentDialog.close()
            }
        }
    }

    PlatformDialogs.DocumentLinkEditorDialog {
        id: documentLinkDialog

        parent: Overlay.overlay

        onSaveRequested: function(payload) {
            if (workspaceController === null) {
                return
            }
            const result = workspaceController.addDocumentLink(payload)
            if (result.ok) {
                documentLinkDialog.close()
            }
        }
    }

    PlatformDialogs.DocumentStructureEditorDialog {
        id: documentStructureDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? workspaceController.createDocumentStructure(payload)
                : workspaceController.updateDocumentStructure(payload)
            if (result.ok) {
                documentStructureDialog.close()
            }
        }
    }
}
