pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectDetail: ({ "id": "", "state": {} })
    property var sectionErrors: ({})

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Material Demand" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["materialDemand"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["materialDemand"] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _matDemandContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _matDemandContent
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasProject
                    title: "No project selected"
                    message: "Select a project to view material demand and reservations."
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._hasProject
                    title: "Material demand tracking"
                    message: "Open the Tasks workspace and select a task to create or manage inventory reservations for this project."
                }
            }
        }
    }
}
