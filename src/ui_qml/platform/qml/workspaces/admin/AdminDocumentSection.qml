import QtQuick
import QtQuick.Layouts
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets
import App.Theme 1.0 as Theme

GridLayout {
    id: root

    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property var selectedDocument: ({})
    property var documentPreviewState: ({})
    property var documentLinkCatalog: ({})
    property var documentStructureCatalog: ({})
    signal documentLinkCreateRequested()
    signal documentStructureCreateRequested()
    signal documentStructureEditRequested(string itemId)

    columns: width > 1480 ? 3 : 1
    columnSpacing: Theme.AppTheme.spacingMd
    rowSpacing: Theme.AppTheme.spacingMd

    PlatformWidgets.DocumentDetailPanel {
        Layout.fillWidth: true
        details: root.selectedDocument
        previewState: root.documentPreviewState
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false

        onOpenRequested: function(targetUrl) {
            if (targetUrl && targetUrl.length > 0) {
                Qt.openUrlExternally(targetUrl)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.documentLinkCatalog.title || "Linked Records"
        summary: root.documentLinkCatalog.subtitle || ""
        catalog: root.documentLinkCatalog
        createActionLabel: "Add Link"
        createEnabled: root.workspaceController
            ? (!root.workspaceController.isBusy && root.selectedDocument.hasSelection)
            : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        secondaryActionLabel: "Remove Link"
        secondaryDanger: true

        onCreateRequested: {
            root.documentLinkCreateRequested()
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.removeDocumentLink(itemId)
            }
        }
    }

    PlatformWidgets.AdminCatalogPanel {
        Layout.fillWidth: true
        title: root.documentStructureCatalog.title || "Document Structures"
        summary: root.documentStructureCatalog.subtitle || ""
        catalog: root.documentStructureCatalog
        createActionLabel: "New Structure"
        createEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
        primaryActionLabel: "Edit"
        secondaryActionLabel: "Toggle Active"

        onCreateRequested: {
            root.documentStructureCreateRequested()
        }

        onPrimaryActionRequested: function(itemId) {
            root.documentStructureEditRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            if (root.workspaceController !== null) {
                root.workspaceController.toggleDocumentStructureActive(itemId)
            }
        }
    }
}
