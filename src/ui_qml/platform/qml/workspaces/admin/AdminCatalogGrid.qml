import QtQuick
import QtQuick.Layouts
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets
import App.Theme 1.0 as Theme

GridLayout {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property var organizationCatalog: ({})
    property var siteCatalog: ({})
    property var departmentCatalog: ({})
    property var employeeCatalog: ({})
    property var userCatalog: ({})
    property var partyCatalog: ({})
    property var documentCatalog: ({})
    signal organizationCreateRequested()
    signal organizationEditRequested(string itemId)
    signal siteCreateRequested()
    signal siteEditRequested(string itemId)
    signal departmentCreateRequested()
    signal departmentEditRequested(string itemId)
    signal employeeCreateRequested()
    signal employeeEditRequested(string itemId)
    signal userCreateRequested()
    signal userEditRequested(string itemId)
    signal partyCreateRequested()
    signal partyEditRequested(string itemId)
    signal documentCreateRequested()
    signal documentInspectRequested(string itemId)
    signal documentEditRequested(string itemId)

    columns: width > 1500 ? 3 : (width > 960 ? 2 : 1)
    columnSpacing: Theme.AppTheme.spacingMd
    rowSpacing: Theme.AppTheme.spacingMd

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.organizationCatalog.title || "Organizations"
        summary: root.organizationCatalog.subtitle || ""
        catalog: root.organizationCatalog
        createActionLabel: "New Organization"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Set Active"

        onCreateRequested: {
            root.organizationCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.organizationEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.setActiveOrganization(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.siteCatalog.title || "Sites"
        summary: root.siteCatalog.subtitle || ""
        catalog: root.siteCatalog
        createActionLabel: "New Site"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.siteCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.siteEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.toggleSiteActive(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.departmentCatalog.title || "Departments"
        summary: root.departmentCatalog.subtitle || ""
        catalog: root.departmentCatalog
        createActionLabel: "New Department"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.departmentCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.departmentEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.toggleDepartmentActive(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.employeeCatalog.title || "Employees"
        summary: root.employeeCatalog.subtitle || ""
        catalog: root.employeeCatalog
        createActionLabel: "New Employee"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.employeeCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.employeeEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.toggleEmployeeActive(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.userCatalog.title || "Users"
        summary: root.userCatalog.subtitle || ""
        catalog: root.userCatalog
        createActionLabel: "New User"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.userCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.userEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.toggleUserActive(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.partyCatalog.title || "Parties"
        summary: root.partyCatalog.subtitle || ""
        catalog: root.partyCatalog
        createActionLabel: "New Party"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.partyCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.partyEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.togglePartyActive(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.documentCatalog.title || "Documents"
        summary: root.documentCatalog.subtitle || ""
        catalog: root.documentCatalog
        createActionLabel: "New Document"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Inspect"
        secondaryActionLabel: "Edit"
        tertiaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.documentCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.documentInspectRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            root.documentEditRequested(itemId)
        }

        onTertiaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.toggleDocumentActive(itemId)
            }
        }
    }
}
