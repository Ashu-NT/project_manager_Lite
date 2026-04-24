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
    radius: Theme.AppTheme.radiusMd
    color: root.errorMessage.length > 0
        ? "#FDECEC"
        : root.feedbackMessage.length > 0
            ? Theme.AppTheme.accentSoft
            : Theme.AppTheme.surfaceAlt
    border.color: root.errorMessage.length > 0 ? "#E28B8B" : Theme.AppTheme.border
    implicitHeight: bannerText.implicitHeight + (Theme.AppTheme.marginMd * 2)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        BusyIndicator {
            visible: root.isLoading || root.isBusy
            running: visible
            implicitWidth: 24
            implicitHeight: 24
        }

        Label {
            id: bannerText

            Layout.fillWidth: true
            text: root.errorMessage.length > 0
                ? root.errorMessage
                : root.feedbackMessage.length > 0
                    ? root.feedbackMessage
                    : root.isBusy
                        ? "Applying change..."
                        : "Loading workspace..."
            color: root.errorMessage.length > 0 ? "#8B1E1E" : Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}
