import QtQuick
import QtQuick.Controls
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs

Item {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController

    function openOrganizationCreate() {
        if (root.workspaceController === null) {
            return
        }
        organizationDialog.openForCreate(root.workspaceController.organizationEditorOptions.moduleOptions || [])
    }

    function openOrganizationEdit(state) {
        organizationDialog.openForEdit(state || {})
    }

    function openSiteCreate() {
        siteDialog.openForCreate()
    }

    function openSiteEdit(state) {
        siteDialog.openForEdit(state || {})
    }

    function openDepartmentCreate() {
        if (root.workspaceController === null) {
            return
        }
        departmentDialog.openForCreate(root.workspaceController.departmentEditorOptions || {})
    }

    function openDepartmentEdit(state) {
        if (root.workspaceController === null) {
            return
        }
        departmentDialog.openForEdit(
            state || {},
            root.workspaceController.departmentEditorOptions || {}
        )
    }

    function openEmployeeCreate() {
        if (root.workspaceController === null) {
            return
        }
        employeeDialog.openForCreate(root.workspaceController.employeeEditorOptions || {})
    }

    function openEmployeeEdit(state) {
        if (root.workspaceController === null) {
            return
        }
        employeeDialog.openForEdit(
            state || {},
            root.workspaceController.employeeEditorOptions || {}
        )
    }

    function openUserCreate() {
        if (root.workspaceController === null) {
            return
        }
        userDialog.openForCreate(root.workspaceController.userEditorOptions || {})
    }

    function openUserEdit(state) {
        if (root.workspaceController === null) {
            return
        }
        userDialog.openForEdit(
            state || {},
            root.workspaceController.userEditorOptions || {}
        )
    }

    function openPartyCreate() {
        if (root.workspaceController === null) {
            return
        }
        partyDialog.openForCreate(root.workspaceController.partyEditorOptions || {})
    }

    function openPartyEdit(state) {
        if (root.workspaceController === null) {
            return
        }
        partyDialog.openForEdit(
            state || {},
            root.workspaceController.partyEditorOptions || {}
        )
    }

    function openDocumentCreate() {
        if (root.workspaceController === null) {
            return
        }
        documentDialog.openForCreate(root.workspaceController.documentEditorOptions || {})
    }

    function openDocumentEdit(state) {
        if (root.workspaceController === null) {
            return
        }
        documentDialog.openForEdit(
            state || {},
            root.workspaceController.documentEditorOptions || {}
        )
    }

    function openDocumentLinkCreate(documentId) {
        documentLinkDialog.openForCreate(documentId || "")
    }

    function openDocumentStructureCreate() {
        if (root.workspaceController === null) {
            return
        }
        documentStructureDialog.openForCreate(
            root.workspaceController.documentStructureEditorOptions || {}
        )
    }

    function openDocumentStructureEdit(state) {
        if (root.workspaceController === null) {
            return
        }
        documentStructureDialog.openForEdit(
            state || {},
            root.workspaceController.documentStructureEditorOptions || {}
        )
    }

    PlatformDialogs.OrganizationEditorDialog {
        id: organizationDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createOrganization(payload)
                : root.workspaceController.updateOrganization(payload)
            if (result.ok) {
                organizationDialog.close()
            }
        }
    }

    PlatformDialogs.SiteEditorDialog {
        id: siteDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createSite(payload)
                : root.workspaceController.updateSite(payload)
            if (result.ok) {
                siteDialog.close()
            }
        }
    }

    PlatformDialogs.DepartmentEditorDialog {
        id: departmentDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createDepartment(payload)
                : root.workspaceController.updateDepartment(payload)
            if (result.ok) {
                departmentDialog.close()
            }
        }
    }

    PlatformDialogs.EmployeeEditorDialog {
        id: employeeDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createEmployee(payload)
                : root.workspaceController.updateEmployee(payload)
            if (result.ok) {
                employeeDialog.close()
            }
        }
    }

    PlatformDialogs.UserEditorDialog {
        id: userDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createUser(payload)
                : root.workspaceController.updateUser(payload)
            if (result.ok) {
                userDialog.close()
            }
        }
    }

    PlatformDialogs.PartyEditorDialog {
        id: partyDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createParty(payload)
                : root.workspaceController.updateParty(payload)
            if (result.ok) {
                partyDialog.close()
            }
        }
    }

    PlatformDialogs.DocumentEditorDialog {
        id: documentDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createDocument(payload)
                : root.workspaceController.updateDocument(payload)
            if (result.ok) {
                documentDialog.close()
            }
        }
    }

    PlatformDialogs.DocumentLinkEditorDialog {
        id: documentLinkDialog

        parent: Overlay.overlay

        onSaveRequested: function(payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = root.workspaceController.addDocumentLink(payload)
            if (result.ok) {
                documentLinkDialog.close()
            }
        }
    }

    PlatformDialogs.DocumentStructureEditorDialog {
        id: documentStructureDialog

        parent: Overlay.overlay

        onSaveRequested: function(mode, payload) {
            if (root.workspaceController === null) {
                return
            }
            const result = mode === "create"
                ? root.workspaceController.createDocumentStructure(payload)
                : root.workspaceController.updateDocumentStructure(payload)
            if (result.ok) {
                documentStructureDialog.close()
            }
        }
    }
}
