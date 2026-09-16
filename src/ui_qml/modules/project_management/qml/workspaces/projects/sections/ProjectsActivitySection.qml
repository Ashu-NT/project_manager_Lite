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
    property var workspaceController: null
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
            Layout.preferredHeight: Math.max(160, activityFeed.implicitHeight) + pagination.implicitHeight
            AppWidgets.ActivityFeed {
                id: activityFeed
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: pagination.top
                items: root.projectActivityModel.items || []
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
