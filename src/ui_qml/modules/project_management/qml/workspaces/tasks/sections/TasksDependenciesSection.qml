pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var dependenciesModel: ({"items":[]})
    property var dependenciesTableModel: null
    property var workspaceController: null
    property bool isBusy: false
    property bool canCreate: false
    property string errorText: ""
    property var dependencyTypeOptions: []
    property var taskDetail: ({})
    property var dependencyImpactPreview: ({})
    property string _selectedId: ""

    signal createRequested()
    signal editRequested(var dependencyData)
    signal deleteRequested(var dependencyData)
    signal openTaskRequested(string taskId)
    signal selectionChanged(var dependencyData)
    signal previewRequested(string dependencyId)

    readonly property var _items: root.dependenciesModel.items || []
    readonly property var _selectedItem: {
        for (let i = 0; i < root._items.length; i++)
            if (String(root._items[i].id || "") === root._selectedId) return root._items[i]
        return null
    }
    readonly property var _state: root._selectedItem ? (root._selectedItem.state || {}) : ({})
    implicitHeight: 520

    function _applyFilters() {
        if (root.workspaceController)
            root.workspaceController.setTaskDependenciesFilters(String(directionFilter.model[directionFilter.currentIndex].value),
                                                                String(typeFilter.model[typeFilter.currentIndex].value))
    }
    function clearSelection() { root._selectedId = ""; root.selectionChanged(null) }
    function openEditSelected() { if (root._selectedItem) root.editRequested(root._selectedItem) }

    ColumnLayout {
        anchors.fill: parent; spacing: Theme.AppTheme.spacingSm
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true; title: "Dependencies"
            subtitle: Number(root.dependenciesModel.predecessorTotal || 0) + " predecessor(s), "
                      + Number(root.dependenciesModel.successorTotal || 0) + " successor(s)"
            busy: root.isBusy; createLabel: root.canCreate ? "Add Dependency" : ""; actions: []
            onCreateRequested: root.createRequested()
        }
        AppWidgets.TableToolbar {
            Layout.fillWidth: true; showFilter: false; showRefresh: false; isBusy: root.isBusy
            searchText: String(root.dependenciesModel.searchText || "")
            searchPlaceholder: "Search related task, code, or WBS..."
            onSearchChanged: function(text) { root.workspaceController.setTaskDependenciesSearch(text) }
            AppControls.ComboBox {
                id: directionFilter; implicitWidth: 135; textRole: "label"
                model: [{"value":"all","label":"All directions"},{"value":"PREDECESSOR","label":"Predecessors"},
                        {"value":"SUCCESSOR","label":"Successors"}]
                onActivated: root._applyFilters()
            }
            AppControls.ComboBox {
                id: typeFilter; implicitWidth: 150; textRole: "label"
                model: [{"value":"all","label":"All relationship types"},{"value":"FS","label":"Finish to Start"},
                        {"value":"FF","label":"Finish to Finish"},{"value":"SS","label":"Start to Start"},
                        {"value":"SF","label":"Start to Finish"}]
                onActivated: root._applyFilters()
            }
        }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: root.errorText.length > 0; tone: "danger"; message: root.errorText }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.AppTheme.spacingMd
            Item {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 360
                AppWidgets.DataTable {
                    anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: pagination.top
                    columns: [{key:"direction",label:"Direction",minWidth:105,flex:0,type:"status",sortable:true},
                              {key:"taskCode",label:"Code",minWidth:90,flex:0,sortable:true},
                              {key:"linkedTask",label:"Related Task",minWidth:180,flex:2,sortable:true},
                              {key:"dependencyType",label:"Type",minWidth:125,flex:1,sortable:true},
                              {key:"lagDays",label:"Lag / Lead",minWidth:90,flex:0,sortable:true},
                              {key:"startDate",label:"Start",minWidth:105,flex:0,sortable:true},
                              {key:"endDate",label:"Finish",minWidth:105,flex:0,sortable:true},
                              {key:"statusLabel",label:"Task Status",minWidth:105,flex:0,type:"status",sortable:true}]
                    sourceModel: root.dependenciesTableModel; sortingMode: "server"
                    sortKey: String(root.dependenciesModel.sortKey || "linkedTask")
                    sortDirection: root.dependenciesModel.sortDirection === "desc" ? Qt.DescendingOrder : Qt.AscendingOrder
                    selectedRowId: root._selectedId; loading: root.isBusy
                    emptyText: root.dependenciesModel.emptyState || "No dependencies match."
                    onRowSelected: function(id) { root._selectedId=id; root.selectionChanged(root._selectedItem); if(id) root.previewRequested(id) }
                    onRowActivated: function(id) { root._selectedId=id; root.selectionChanged(root._selectedItem); if(id) root.previewRequested(id) }
                    onSortRequested: function(key, direction) { root.workspaceController.setTaskDependenciesSort(key, direction) }
                }
                AppWidgets.TablePaginationBar {
                    id: pagination; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                    currentPage: Number(root.dependenciesModel.page || 1); pageSize: Number(root.dependenciesModel.pageSize || 25)
                    totalItems: Number(root.dependenciesModel.total || 0); busy: root.isBusy
                    onPageRequested: function(page) { root.workspaceController.setTaskDependenciesPage(page) }
                    onPageSizeRequested: function(size) { root.workspaceController.setTaskDependenciesPageSize(size) }
                }
            }
            AppWidgets.InspectorPanel {
                Layout.preferredWidth: Theme.AppTheme.inspectorWidth; Layout.fillHeight: true
                visible: root._selectedItem !== null; title: root._selectedItem ? String(root._selectedItem.linkedTask || "") : ""
                statusLabel: root._selectedItem ? String(root._selectedItem.direction || "") : ""
                sections: root._selectedItem ? [{"label":"Relationship","value":String(root._selectedItem.dependencyType || "")},
                                                {"label":"Lag / Lead","value":String(root._selectedItem.lagDays || "0d")},
                                                {"label":"Schedule","value":String(root._selectedItem.startDate || "--") + " - " + String(root._selectedItem.endDate || "--")}] : []
                onCloseRequested: root.clearSelection()
                RowLayout {
                    Layout.fillWidth: true
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Edit"; iconName: "edit"; onClicked: root.editRequested(root._selectedItem) }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Open Task"; iconName: "chevron_right"; onClicked: root.openTaskRequested(String(root._state.linkedTaskId || "")) }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Remove"; iconName: "delete"; danger: true; onClicked: root.deleteRequested(root._selectedItem) }
                }
            }
        }
    }
}
