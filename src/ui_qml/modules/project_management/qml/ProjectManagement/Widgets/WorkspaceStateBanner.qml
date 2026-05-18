import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property bool isLoading: false
    property bool isBusy: false
    property string errorMessage: ""
    property string feedbackMessage: ""

    visible: root.isLoading || root.isBusy || root.errorMessage.length > 0 || root.feedbackMessage.length > 0
    radius: Theme.AppTheme.radiusSm
    color: root.errorMessage.length > 0
        ? Theme.AppTheme.dangerSoft
        : root.feedbackMessage.length > 0
            ? Theme.AppTheme.successSoft
            : Theme.AppTheme.infoSoft
    border.color: root.errorMessage.length > 0
        ? Theme.AppTheme.danger
        : root.feedbackMessage.length > 0
            ? Theme.AppTheme.success
            : Theme.AppTheme.accent
    border.width: 1
    implicitHeight: bannerRow.implicitHeight + (Theme.AppTheme.spacingSm * 2)

    RowLayout {
        id: bannerRow
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.spacingSm
        spacing: Theme.AppTheme.spacingSm

        BusyIndicator {
            visible: root.isLoading || root.isBusy
            running: visible
            implicitWidth: 20
            implicitHeight: 20
        }

        Label {
            Layout.fillWidth: true
            text: root.errorMessage.length > 0
                ? root.errorMessage
                : root.feedbackMessage.length > 0
                    ? root.feedbackMessage
                    : root.isBusy
                        ? "Applying change..."
                        : "Loading workspace..."
            color: root.errorMessage.length > 0
                ? Theme.AppTheme.danger
                : root.feedbackMessage.length > 0
                    ? Theme.AppTheme.success
                    : Theme.AppTheme.accent
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}
