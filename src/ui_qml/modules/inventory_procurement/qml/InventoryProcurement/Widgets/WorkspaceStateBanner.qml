import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property bool isLoading: false
    property bool isBusy: false
    property string errorMessage: ""
    property string feedbackMessage: ""

    spacing: Theme.AppTheme.spacingSm
    visible: root.isLoading || root.isBusy || root.errorMessage.length > 0 || root.feedbackMessage.length > 0

    Rectangle {
        visible: root.isLoading || root.isBusy
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusMd
        color: Theme.AppTheme.surfaceAlt
        border.color: Theme.AppTheme.border
        implicitHeight: statusText.implicitHeight + Theme.AppTheme.spacingMd * 2

        Text {
            id: statusText
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.spacingMd
            wrapMode: Text.WordWrap
            color: Theme.AppTheme.textPrimary
            text: root.isBusy ? "Saving inventory changes..." : "Loading inventory workspace..."
        }
    }

    Rectangle {
        visible: root.errorMessage.length > 0
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusMd
        color: "#FDECEC"
        border.color: "#E36A6A"
        implicitHeight: errorText.implicitHeight + Theme.AppTheme.spacingMd * 2

        Text {
            id: errorText
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.spacingMd
            wrapMode: Text.WordWrap
            color: "#8B1E1E"
            text: root.errorMessage
        }
    }

    Rectangle {
        visible: root.feedbackMessage.length > 0
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusMd
        color: "#E9F7EE"
        border.color: "#5CA36B"
        implicitHeight: feedbackText.implicitHeight + Theme.AppTheme.spacingMd * 2

        Text {
            id: feedbackText
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.spacingMd
            wrapMode: Text.WordWrap
            color: "#1E5A2C"
            text: root.feedbackMessage
        }
    }
}
