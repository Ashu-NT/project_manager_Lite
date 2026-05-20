import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var commentsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var presenceModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedTaskId: ""
    property bool isBusy: false
    property bool canCompose: false

    signal composeRequested()
    signal markReadRequested(string taskId)
    signal refreshRequested()

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: "Task Collaboration"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: "Comments, mentions, attachments, linked documents, and active task presence now sit directly on the task workspace."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppControls.PrimaryButton {
                text: "Post Update"
                iconName: "collaboration"
                enabled: root.canCompose && !root.isBusy
                onClicked: root.composeRequested()
            }

            AppControls.PrimaryButton {
                text: "Mark Mentions Read"
                iconName: "approve"
                enabled: root.selectedTaskId.length > 0 && !root.isBusy
                onClicked: root.markReadRequested(root.selectedTaskId)
            }

            AppControls.PrimaryButton {
                text: "Refresh"
                iconName: "refresh"
                enabled: !root.isBusy
                onClicked: root.refreshRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 1180 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            ProjectManagementWidgets.RecordListCard {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                title: String(root.commentsModel.title || "")
                subtitle: String(root.commentsModel.subtitle || "")
                emptyState: String(root.commentsModel.emptyState || "")
                items: root.commentsModel.items || []
            }

            ProjectManagementWidgets.RecordListCard {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                title: String(root.presenceModel.title || "")
                subtitle: String(root.presenceModel.subtitle || "")
                emptyState: String(root.presenceModel.emptyState || "")
                items: root.presenceModel.items || []
            }
        }
    }
}
