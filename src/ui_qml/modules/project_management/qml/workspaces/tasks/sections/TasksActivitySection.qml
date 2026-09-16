pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var activityModel: ({"items":[]})
    property var workspaceController: null
    property string errorText: ""
    property bool isBusy: false
    property real availableHeight: 0
    implicitHeight: Math.max(content.implicitHeight, root.availableHeight)
    ColumnLayout {
        id: content
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
        height: root.implicitHeight
        spacing: Theme.AppTheme.spacingSm
        AppWidgets.TableToolbar {
            Layout.fillWidth: true; showFilter: false; showRefresh: true; isBusy: root.isBusy
            searchText: String(root.activityModel.searchText || ""); searchPlaceholder: "Search event or summary..."
            onSearchChanged: function(text) { root.workspaceController.setTaskActivitySearch(text) }
            onRefreshRequested: root.workspaceController.loadSelectedTaskActivity()
            AppControls.ComboBox {
                implicitWidth: 145; textRole: "label"
                model: [{"value":"all","label":"All activity"},{"value":"task","label":"Task changes"},
                        {"value":"assignments","label":"Assignment changes"}]
                onActivated: function(index) { root.workspaceController.setTaskActivityCategory(String(model[index].value)) }
            }
        }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: root.errorText.length > 0; tone: "danger"; message: root.errorText }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: Math.max(160, activityFeed.implicitHeight) + pagination.implicitHeight
            AppWidgets.ActivityFeed {
                id: activityFeed
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: pagination.top
                items: root.activityModel.items || []
                emptyText: root.activityModel.emptyState || "No activity recorded."
            }
            AppWidgets.TablePaginationBar {
                id: pagination; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: Number(root.activityModel.page || 1); pageSize: Number(root.activityModel.pageSize || 25)
                totalItems: Number(root.activityModel.total || 0); busy: root.isBusy
                onPageRequested: function(page) { root.workspaceController.setTaskActivityPage(page) }
                onPageSizeRequested: function(size) { root.workspaceController.setTaskActivityPageSize(size) }
            }
        }
    }
}
