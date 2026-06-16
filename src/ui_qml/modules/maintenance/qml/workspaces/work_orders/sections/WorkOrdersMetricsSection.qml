pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var metrics: []

    width:          parent ? parent.width : 0
    implicitHeight: _strip.implicitHeight

    AppWidgets.KpiStrip {
        id: _strip
        anchors.left:  parent.left
        anchors.right: parent.right
        metrics: root.metrics
    }
}
