pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls


Item {
    id: root

    property string destinationLabel: ""
    signal selectProjectRequested()

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.workspaceBackground
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(420, parent.width - Theme.AppTheme.marginXl * 2)
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "Select a project to continue"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.subtitleSize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: (root.destinationLabel.length > 0 ? root.destinationLabel : "This workspace")
                + " requires an active project. Pin one from the project context bar above to continue."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        AppControls.PrimaryButton {
            Layout.alignment: Qt.AlignHCenter
            text: "Select Project"
            onClicked: root.selectProjectRequested()
        }
    }

    Accessible.role: Accessible.StaticText
    Accessible.name: "Project context required"
}
