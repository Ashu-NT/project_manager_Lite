import QtQuick
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var heatmapModel: AppMock.MockFactory.catalog()
    property var recentActionsModel: AppMock.MockFactory.catalog()

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.heatmapModel.title || "Portfolio Heatmap"
            subtitle: root.heatmapModel.subtitle || ""
            emptyState: root.heatmapModel.emptyState || ""
            items: root.heatmapModel.items || []
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.recentActionsModel.title || "Recent Actions"
            subtitle: root.recentActionsModel.subtitle || ""
            emptyState: root.recentActionsModel.emptyState || ""
            items: root.recentActionsModel.items || []
        }
    }
}
