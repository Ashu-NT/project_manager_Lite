pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Models 1.0 as AppModels
import Platform.Components 1.0 as PlatformComponents

// Employee Detail's Documents tab -- the first real production consumer of
// the generic Platform DocumentLink capability (see employee_documents.py).
// Shows only Documents linked to this exact Employee, using the same
// canonical AdminEntityWorkspace stack every other paginated sub-tab
// (Department's/Site's own Employees tab, etc.) already uses. Row
// activation opens the real, canonical Document Detail -- never a second
// copy of Document metadata editing here. Unlinking is a relationship
// removal only (see "Remove from Employee" below) -- it can never delete
// the underlying Document; a true delete remains a Documents-workspace-only
// capability with its own authorization, never exposed from this page.
Item {
    id: root

    property bool canWrite: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property real viewportHeight: 420

    property var catalog: ({ "items": [] })
    property var columns: []
    property string selectedRowId: ""
    property string searchText: ""
    property var statusFilterOptions: []
    property string statusFilter: ""
    property var typeFilterOptions: []
    property string typeFilter: ""

    signal addDocumentRequested()
    signal rowSelected(string id)
    signal rowActivated(string documentId)
    signal unlinkRequested(string linkId)
    signal refreshRequested()
    signal searchChanged(string text)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal clearFiltersRequested()
    signal statusFilterRequested(string value)
    signal typeFilterRequested(string value)

    width: parent ? parent.width : 0
    height: root.viewportHeight

    // Selection is tracked locally (not controller-owned) -- Documents has
    // no cross-page-reload selection requirement the way Organizations'
    // own bulk-archive flow does, so there is no need to promote this to
    // controller state for a first vertical slice.
    property var _selectedRowIds: []

    function _toggleSelection(rowId, selected) {
        const current = root._selectedRowIds.slice()
        const index = current.indexOf(rowId)
        if (selected && index < 0) current.push(rowId)
        else if (!selected && index >= 0) current.splice(index, 1)
        root._selectedRowIds = current
    }

    function _linkIdForRow(rowId) {
        const items = root.catalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === rowId) return String((items[i].state || {}).linkId || "")
        }
        return ""
    }

    AppModels.DynamicTableModel {
        id: _tableModel
        rows: root.catalog.items || []
    }

    PlatformComponents.AdminEntityWorkspace {
        id: _workspace
        anchors.fill: parent
        sectionTitle: "Documents"
        entityLabel: "Document"
        catalog: root.catalog
        catalogModel: _tableModel
        tableId: "employee.detail.documents.table"
        columns: root.columns
        canCreate: root.canWrite
        createLabel: "Add Document"
        isBusy: root.busy
        isLoading: false
        errorMessage: root.errorMessage
        feedbackMessage: root.feedbackMessage
        selectedRowId: root.selectedRowId
        showSearch: true
        searchText: root.searchText
        pageSizeOptions: [25, 50, 100]
        multiSelect: root.canWrite
        selectedRowIds: root._selectedRowIds
        bulkActions: [
            { "id": "unlink", "label": "Remove from Employee", "icon": "delete", "danger": true, "enabled": true }
        ]

        AppControls.ComboBox {
            id: _typeFilterCombo
            Layout.preferredWidth: 160
            model: root.typeFilterOptions
            textRole: "label"
            valueRole: "value"
            currentIndex: {
                for (let i = 0; i < root.typeFilterOptions.length; i += 1) {
                    if (root.typeFilterOptions[i].value === root.typeFilter) return i
                }
                return 0
            }
            onActivated: root.typeFilterRequested(String(currentValue || ""))
        }

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

        onCreateRequested: root.addDocumentRequested()
        onRowSelected: function(id) { root.rowSelected(id) }
        onRowActivated: function(id) { root.rowActivated(id) }
        onRefreshRequested: root.refreshRequested()
        onSearchChanged: function(text) { root.searchChanged(text) }
        onPageRequested: function(page) { root.pageRequested(page) }
        onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        onClearFiltersRequested: root.clearFiltersRequested()
        onRowSelectionToggled: function(rowId, selected) { root._toggleSelection(rowId, selected) }
        onSelectAllToggled: function(allSelected) {
            if (allSelected) {
                root._selectedRowIds = (root.catalog.items || []).map(function(item) { return item.id })
            } else {
                root._selectedRowIds = []
            }
        }
        onBulkActionRequested: function(actionId) {
            if (actionId !== "unlink") return
            const ids = root._selectedRowIds.slice()
            for (let i = 0; i < ids.length; i += 1) {
                const linkId = root._linkIdForRow(ids[i])
                if (linkId.length > 0) root.unlinkRequested(linkId)
            }
            root._selectedRowIds = []
        }
    }
}
