pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import "../OwnerTimesheetsColumnConfig.js" as ColumnConfig

AppControls.CenteredDialog {
    id: root

    property var workspaceController: null
    title: "Previous Timesheets"
    modal: true
    width: Math.min(parent ? parent.width - 48 : 900, 900)
    height: Math.min(parent ? parent.height - 48 : 620, 620)

    contentItem: Item {
        AppWidgets.DataTable {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: historyPagination.top
            columns: ColumnConfig.historyColumns()
            sourceModel: root.workspaceController ? root.workspaceController.historyTableModel : null
            sortingMode: "none"
            loading: root.workspaceController ? root.workspaceController.isLoading : false
            emptyText: "No submitted timesheet history is available."
        }

        AppWidgets.TablePaginationBar {
            id: historyPagination
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            currentPage: root.workspaceController ? root.workspaceController.historyPage : 1
            pageSize: root.workspaceController ? root.workspaceController.historyPageSize : 12
            totalItems: root.workspaceController ? root.workspaceController.historyTotal : 0
            busy: root.workspaceController ? root.workspaceController.isLoading : false
            onPageRequested: function(page) {
                if (root.workspaceController) root.workspaceController.setHistoryPage(page)
            }
        }
    }

    footer: AppControls.DialogActionFooter {
        Item { Layout.fillWidth: true }
        AppControls.PrimaryButton {
            text: "Close"
            iconName: "close"
            onClicked: root.close()
        }
    }
}
