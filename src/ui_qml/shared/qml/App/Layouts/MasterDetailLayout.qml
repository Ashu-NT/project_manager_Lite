pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

SplitView {
    id: root

    default property alias masterContent: masterPane.data
    property alias detailContent: detailPane.data
    property int masterMinWidth: 280
    property int detailMinWidth: 300

    orientation: Qt.Horizontal
    handle: Rectangle {
        implicitWidth: 1
        color: SplitHandle.hovered || SplitHandle.pressed
            ? Theme.AppTheme.accent
            : Theme.AppTheme.divider
    }

    Item {
        id: masterPane
        SplitView.minimumWidth: root.masterMinWidth
        SplitView.preferredWidth: 340
        SplitView.fillHeight: true
    }

    Item {
        id: detailPane
        SplitView.minimumWidth: root.detailMinWidth
        SplitView.fillWidth: true
        SplitView.fillHeight: true
    }
}
