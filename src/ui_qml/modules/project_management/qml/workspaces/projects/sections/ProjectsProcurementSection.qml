pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectDetail: ({ "id": "" })
    property var sectionErrors: ({})

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Procurement" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["procurement"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["procurement"] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _procContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _procContent
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
                    message: "Select a project to view procurement commitments."
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._hasProject
                    title: "Procurement commitments"
                    message: "Open the Financials workspace to review purchase requisitions and committed procurement costs linked to this project."
                }
            }
        }
    }
}
