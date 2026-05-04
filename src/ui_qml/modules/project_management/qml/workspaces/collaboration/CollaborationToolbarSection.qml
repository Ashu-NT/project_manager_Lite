import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property bool isBusy: false

    signal refreshRequested()

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

    RowLayout {
        id: contentLayout

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            Label {
                Layout.fillWidth: true
                text: "Collaboration inbox and workflow feed"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "QML now covers the workspace-level mention inbox, workflow notifications, recent activity, and active presence. Task-by-task posting still remains in the legacy task dialog for now."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        AppControls.PrimaryButton {
            text: "Refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }
    }
}
