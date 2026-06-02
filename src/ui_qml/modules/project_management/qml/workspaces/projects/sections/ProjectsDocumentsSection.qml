pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var sectionErrors: ({})

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Documents" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["documents"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["documents"] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _documentsEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            AppWidgets.EmptyState {
                id: _documentsEmpty
                anchors.top: parent.top
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                title: "Project documents"
                message: "Document management is not yet configured for this project."
            }
        }
    }
}
