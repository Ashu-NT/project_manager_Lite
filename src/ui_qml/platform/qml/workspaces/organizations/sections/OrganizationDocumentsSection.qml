pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Models 1.0 as AppModels
import Platform.Components 1.0 as PlatformComponents
import workspaces.documents 1.0 as DocumentsWorkspace

// Organization Detail's Documents tab: same tenant-scoped, paginated
// pattern as Sites/Departments/Employees for the LIST itself. Row
// activation to the full nested detail page is different, though: unlike
// those entities' detail pages (which only need the row's own state),
// AdminDocumentsDetailPage also needs `selectedDocument`/`documentPreview`/
// `documentLinks`, which the shared workspaceController populates via
// `selectDocument(id)` -- and that call is itself STILL active-organization
// -scoped internally (DocumentService.list_documents()/_require_document_
// in_context() both resolve the active org, not an explicit one). Opening
// the nested detail for a document that belongs to a DIFFERENT
// (non-active) organization would silently resolve the wrong document's
// focus state. So row activation to the full detail page is gated to only
// the organization the caller is actually viewing AND has switched into
// (`isViewingActiveOrganization`, the same flag that already gates
// "+ New") -- see the Phase K Documents report for the full reasoning.
// All list state (catalog/page/search/filter/selection) is owned by the
// orchestrator (AdminOrganizationDetailPage.qml); this section is
// presentational and emits signals for every user action.
Item {
    id: root

    property var platformCatalog: null
    property var workspaceController: null
    property bool canWrite: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property real viewportHeight: 420

    property var catalog: ({ "items": [] })
    property var columns: []
    property bool canCreate: false
    property bool isViewingActiveOrganization: false
    property string selectedRowId: ""
    property string searchText: ""
    property var statusFilterOptions: []
    property string statusFilter: ""
    property bool detailOpen: false
    property var selectedDocumentItem: null

    signal createRequested()
    signal rowSelected(string id)
    signal rowActivated(string id)
    signal refreshRequested()
    signal searchChanged(string text)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal clearFiltersRequested()
    signal statusFilterRequested(string value)
    signal detailBackRequested()
    signal detailActionRequested(string actionId)
    signal documentLinkCreateRequested()

    width: parent ? parent.width : 0
    height: root.viewportHeight

    AppModels.DynamicTableModel {
        id: _tableModel
        rows: root.catalog.items || []
    }

    PlatformComponents.AdminEntityWorkspace {
        id: _workspace
        anchors.fill: parent
        visible: !root.detailOpen
        sectionTitle: "Documents"
        entityLabel: "Document"
        catalog: root.catalog
        catalogModel: _tableModel
        tableId: "organization.detail.documents.table"
        columns: root.columns
        canCreate: root.canCreate
        isBusy: root.busy
        isLoading: false
        errorMessage: root.errorMessage
        feedbackMessage: root.feedbackMessage
        selectedRowId: root.selectedRowId
        showSearch: true
        searchText: root.searchText
        pageSizeOptions: [25, 50, 100]

        AppControls.ComboBox {
            id: _statusFilterCombo
            Layout.preferredWidth: 150
            model: root.statusFilterOptions
            textRole: "label"
            valueRole: "value"
            currentIndex: {
                for (let i = 0; i < root.statusFilterOptions.length; i += 1) {
                    if (root.statusFilterOptions[i].value === root.statusFilter) return i
                }
                return 0
            }
            onActivated: root.statusFilterRequested(String(currentValue || ""))
        }

        onCreateRequested: root.createRequested()
        onRowSelected: function(id) { root.rowSelected(id) }
        onRowActivated: function(id) {
            root.rowSelected(id)
            if (root.isViewingActiveOrganization) {
                root.rowActivated(id)
            }
        }
        onRefreshRequested: root.refreshRequested()
        onSearchChanged: function(text) { root.searchChanged(text) }
        onPageRequested: function(page) { root.pageRequested(page) }
        onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        onClearFiltersRequested: root.clearFiltersRequested()
    }

    Loader {
        anchors.fill: parent
        active: root.detailOpen && root.isViewingActiveOrganization
        visible: active
        asynchronous: true

        sourceComponent: Component {
            DocumentsWorkspace.AdminDocumentsDetailPage {
                document: root.selectedDocumentItem || ({})
                canWrite: root.canWrite
                selectedDocument: root.workspaceController ? root.workspaceController.selectedDocument : ({})
                documentPreviewState: root.workspaceController ? root.workspaceController.documentPreview : ({})
                documentLinkCatalog: root.workspaceController ? root.workspaceController.documentLinks : ({ "items": [] })
                workspaceController: root.workspaceController
                busy: root.busy
                errorMessage: root.errorMessage
                feedbackMessage: root.feedbackMessage

                onBackRequested: root.detailBackRequested()
                onActionRequested: function(actionId) { root.detailActionRequested(actionId) }
                onDocumentLinkCreateRequested: root.documentLinkCreateRequested()
            }
        }
    }
}
