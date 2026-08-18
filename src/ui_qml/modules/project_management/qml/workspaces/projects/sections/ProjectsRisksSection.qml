pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as PMWidgets

Item {
    id: root

    property var sectionErrors: ({})
    property var projectRisksModel: ({
        "title": "Risks", "subtitle": "", "emptyState": "No risks have been logged for this project yet.", "items": []
    })

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Risks" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["risks"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["risks"] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _risksCard.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            PMWidgets.RecordListCard {
                id: _risksCard
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                subtitle: root.projectRisksModel.subtitle || ""
                emptyState: root.projectRisksModel.emptyState || "No risks have been logged for this project yet."
                items: root.projectRisksModel.items || []
            }
        }
    }
}
