pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var sectionErrors: ({})
    property var projectActivityModel: ({"items":[]})
    property var projectActivityTableModel: null
    property var workspaceController: null
    property bool isBusy: false
    property real availableHeight: 0
    readonly property var _items: root.projectActivityModel.items || []
    readonly property int _tableHeight: Math.max(
        120,
        Theme.AppTheme.normalRowHeight
            + Math.max(root._items.length, 1) * Theme.AppTheme.compactRowHeight
            + 1
    )
    implicitHeight: Math.max(content.implicitHeight, root.availableHeight)
    ColumnLayout {
        id: content
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
        height: root.implicitHeight
        spacing: Theme.AppTheme.spacingSm
        AppWidgets.TableToolbar {
            Layout.fillWidth: true; showFilter: false; showRefresh: true; isBusy: root.isBusy
            searchText: String(root.projectActivityModel.searchText || "")
            searchPlaceholder: "Search event or summary..."
            onSearchChanged: function(text) { root.workspaceController.setProjectActivitySearch(text) }
            onRefreshRequested: root.workspaceController.loadProjectActivity()
            AppControls.ComboBox {
                implicitWidth: 145; textRole: "label"
                model: [{"value":"all","label":"All activity"},{"value":"project","label":"Project changes"},
                        {"value":"resources","label":"Resource changes"}]
                onActivated: function(index) { root.workspaceController.setProjectActivityCategory(String(model[index].value)) }
            }
        }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: String(root.sectionErrors["activity"] || "").length > 0; tone: "danger"; message: String(root.sectionErrors["activity"] || "") }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: root._tableHeight + pagination.implicitHeight
            AppWidgets.DataTable {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: pagination.top
                columns: [{key:"occurredAt",label:"When",minWidth:115,flex:0},
                          {key:"actorLabel",label:"Actor",minWidth:130,flex:1},
                          {key:"eventLabel",label:"Event",minWidth:150,flex:1.2},
                          {key:"sourceLabel",label:"Source",minWidth:110,flex:0,type:"status"},
                          {key:"summary",label:"Summary",minWidth:240,flex:2.5}]
                sourceModel: root.projectActivityTableModel; sortingMode: "none"; loading: root.isBusy
                emptyText: root.projectActivityModel.emptyState || "No activity recorded."
            }
            AppWidgets.TablePaginationBar {
                id: pagination; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: Number(root.projectActivityModel.page || 1); pageSize: Number(root.projectActivityModel.pageSize || 25)
                totalItems: Number(root.projectActivityModel.total || 0); busy: root.isBusy
                onPageRequested: function(page) { root.workspaceController.setProjectActivityPage(page) }
                onPageSizeRequested: function(size) { root.workspaceController.setProjectActivityPageSize(size) }
            }
        }
    }
}
