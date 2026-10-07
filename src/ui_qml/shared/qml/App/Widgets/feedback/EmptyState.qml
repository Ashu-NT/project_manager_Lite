import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property string title: "No records found"
    property string message: ""
    // Optional single resolution action (e.g. "Create organization" for a
    // true-empty dataset, "Clear filters" for a no-results search/filter
    // state). Hidden entirely when actionLabel is empty -- most EmptyState
    // consumers remain purely informational.
    property string actionLabel: ""
    signal actionRequested()

    implicitHeight: column.implicitHeight + Theme.AppTheme.spacingLg * 2

    ColumnLayout {
        id: column
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingSm
        width: Math.min(parent.width, 320)

        AppControls.Label {
            Layout.fillWidth: true
            text: root.title
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.message.length > 0
            text: root.message
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        AppControls.PrimaryButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: Theme.AppTheme.spacingXs
            visible: root.actionLabel.length > 0
            text: root.actionLabel
            onClicked: root.actionRequested()
        }
    }
}
