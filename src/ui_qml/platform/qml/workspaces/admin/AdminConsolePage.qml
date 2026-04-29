import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets
import App.Theme 1.0 as Theme

AppLayouts.WorkspaceFrame {
    id: root

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
    property var organizationCatalog: root.workspaceController
        ? root.workspaceController.organizations
        : ({
            "title": "Organizations",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var siteCatalog: root.workspaceController
        ? root.workspaceController.sites
        : ({
            "title": "Sites",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var departmentCatalog: root.workspaceController
        ? root.workspaceController.departments
        : ({
            "title": "Departments",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var employeeCatalog: root.workspaceController
        ? root.workspaceController.employees
        : ({
            "title": "Employees",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var userCatalog: root.workspaceController
        ? root.workspaceController.users
        : ({
            "title": "Users",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var partyCatalog: root.workspaceController
        ? root.workspaceController.parties
        : ({
            "title": "Parties",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var documentCatalog: root.workspaceController
        ? root.workspaceController.documents
        : ({
            "title": "Documents",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var selectedDocument: root.workspaceController
        ? root.workspaceController.selectedDocument
        : ({
            "hasSelection": false,
            "documentId": "",
            "title": "Select a document",
            "summary": "",
            "badges": [],
            "metadataRows": [],
            "notes": ""
        })
    property var documentPreviewState: root.workspaceController
        ? root.workspaceController.documentPreview
        : ({
            "statusLabel": "No document selected",
            "summary": "",
            "canOpen": false,
            "openLabel": "Open Source",
            "openTargetUrl": ""
        })
    property var documentLinkCatalog: root.workspaceController
        ? root.workspaceController.documentLinks
        : ({
            "title": "Linked Records",
            "subtitle": "",
            "emptyState": "",
            "items": []
        })
    property var documentStructureCatalog: root.workspaceController
        ? root.workspaceController.documentStructures
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

    function openOrganizationEdit(itemId) {
        const item = root.catalogItemById(root.organizationCatalog, itemId)
        if (item !== null) {
            dialogHost.openOrganizationEdit(item.state || {})
        }
    }

    function openSiteEdit(itemId) {
        const item = root.catalogItemById(root.siteCatalog, itemId)
        if (item !== null) {
            dialogHost.openSiteEdit(item.state || {})
        }
    }

    function openDepartmentEdit(itemId) {
        const item = root.catalogItemById(root.departmentCatalog, itemId)
        if (item !== null) {
            dialogHost.openDepartmentEdit(item.state || {})
        }
    }

    function openEmployeeEdit(itemId) {
        const item = root.catalogItemById(root.employeeCatalog, itemId)
        if (item !== null) {
            dialogHost.openEmployeeEdit(item.state || {})
        }
    }

    function openUserEdit(itemId) {
        const item = root.catalogItemById(root.userCatalog, itemId)
        if (item !== null) {
            dialogHost.openUserEdit(item.state || {})
        }
    }

    function openPartyEdit(itemId) {
        const item = root.catalogItemById(root.partyCatalog, itemId)
        if (item !== null) {
            dialogHost.openPartyEdit(item.state || {})
        }
    }

    function inspectDocument(itemId) {
        if (root.workspaceController !== null) {
            root.workspaceController.selectDocument(itemId)
        }
    }

    function openDocumentEdit(itemId) {
        const item = root.catalogItemById(root.documentCatalog, itemId)
        if (item !== null) {
            root.inspectDocument(itemId)
            dialogHost.openDocumentEdit(item.state || {})
        }
    }

    function openDocumentLinkCreate() {
        if (root.selectedDocument.hasSelection) {
            dialogHost.openDocumentLinkCreate(root.selectedDocument.documentId || "")
        }
    }

    function openDocumentStructureEdit(itemId) {
        const item = root.catalogItemById(root.documentStructureCatalog, itemId)
        if (item !== null) {
            dialogHost.openDocumentStructureEdit(item.state || {})
        }
    }

    title: root.workspaceController ? (root.workspaceController.overview.title || root.workspaceModel.title) : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

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
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            AdminMetricsSection {
                Layout.fillWidth: true
                metrics: root.workspaceController ? (root.workspaceController.overview.metrics || []) : []
            }

            AdminCatalogGrid {
                Layout.fillWidth: true
                workspaceController: root.workspaceController
                organizationCatalog: root.organizationCatalog
                siteCatalog: root.siteCatalog
                departmentCatalog: root.departmentCatalog
                employeeCatalog: root.employeeCatalog
                userCatalog: root.userCatalog
                partyCatalog: root.partyCatalog
                documentCatalog: root.documentCatalog

                onOrganizationCreateRequested: dialogHost.openOrganizationCreate()
                onOrganizationEditRequested: function(itemId) { root.openOrganizationEdit(itemId) }
                onSiteCreateRequested: dialogHost.openSiteCreate()
                onSiteEditRequested: function(itemId) { root.openSiteEdit(itemId) }
                onDepartmentCreateRequested: dialogHost.openDepartmentCreate()
                onDepartmentEditRequested: function(itemId) { root.openDepartmentEdit(itemId) }
                onEmployeeCreateRequested: dialogHost.openEmployeeCreate()
                onEmployeeEditRequested: function(itemId) { root.openEmployeeEdit(itemId) }
                onUserCreateRequested: dialogHost.openUserCreate()
                onUserEditRequested: function(itemId) { root.openUserEdit(itemId) }
                onPartyCreateRequested: dialogHost.openPartyCreate()
                onPartyEditRequested: function(itemId) { root.openPartyEdit(itemId) }
                onDocumentCreateRequested: dialogHost.openDocumentCreate()
                onDocumentInspectRequested: function(itemId) { root.inspectDocument(itemId) }
                onDocumentEditRequested: function(itemId) { root.openDocumentEdit(itemId) }
            }

            AdminDocumentSection {
                Layout.fillWidth: true
                workspaceController: root.workspaceController
                selectedDocument: root.selectedDocument
                documentPreviewState: root.documentPreviewState
                documentLinkCatalog: root.documentLinkCatalog
                documentStructureCatalog: root.documentStructureCatalog

                onDocumentLinkCreateRequested: root.openDocumentLinkCreate()
                onDocumentStructureCreateRequested: dialogHost.openDocumentStructureCreate()
                onDocumentStructureEditRequested: function(itemId) { root.openDocumentStructureEdit(itemId) }
            }

            PlatformWidgets.AccessSecurityPanel {
                Layout.fillWidth: true
                controller: root.accessController
            }

            AdminSupportSection {
                Layout.fillWidth: true
                supportController: root.supportController
            }

            AdminOverviewSections {
                Layout.fillWidth: true
                sections: root.workspaceController ? (root.workspaceController.overview.sections || []) : []
            }
        }
    }

    AdminDialogHost {
        id: dialogHost
        workspaceController: root.workspaceController
    }
}
