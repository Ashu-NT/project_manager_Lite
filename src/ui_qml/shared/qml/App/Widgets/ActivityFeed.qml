pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Reusable timeline activity feed.
// items: [{ title, metaText, statusLabel }]
Item {
    id: root

    property var    items:     []
    property string emptyText: "No activity recorded"

    signal itemActivated(var item)

    implicitHeight: root.items.length === 0
        ? _empty.implicitHeight
        : _list.contentHeight

    AppWidgets.EmptyState {
        id: _empty
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width, 320)
        visible: root.items.length === 0
        title: root.emptyText
    }

    ListView {
        id: _list
        anchors.fill: parent
        visible: root.items.length > 0
        model: root.items
        interactive: false

        delegate: Item {
            id: _row
            required property var modelData
            required property int index

            width: _list.width
            height: 44

            readonly property string _status: String(_row.modelData.statusLabel || "")
            readonly property bool _clickable: String(_row.modelData.routeId || "").length > 0

            Rectangle {
                id: _dot
                anchors.left:           parent.left
                anchors.leftMargin:     Theme.AppTheme.spacingSm
                anchors.verticalCenter: parent.verticalCenter
                width: 7; height: 7; radius: 4
                color: {
                    const s = _row._status.toLowerCase()
                    if (s.indexOf("success") >= 0 || s.indexOf("complet") >= 0
                            || s.indexOf("approv") >= 0 || s.indexOf("done") >= 0)
                        return Theme.AppTheme.success
                    if (s.indexOf("danger") >= 0 || s.indexOf("fail") >= 0
                            || s.indexOf("error") >= 0 || s.indexOf("reject") >= 0)
                        return Theme.AppTheme.danger
                    if (s.indexOf("warn") >= 0 || s.indexOf("pending") >= 0)
                        return Theme.AppTheme.warning
                    return Theme.AppTheme.textMuted
                }
            }

            Rectangle {
                visible: _row.index < _list.count - 1
                anchors.horizontalCenter: _dot.horizontalCenter
                anchors.top:             _dot.bottom
                anchors.topMargin:       2
                anchors.bottom:          parent.bottom
                width: 1
                color: Theme.AppTheme.divider
            }

            ColumnLayout {
                anchors.left:           _dot.right
                anchors.leftMargin:     Theme.AppTheme.spacingSm
                anchors.right:          parent.right
                anchors.rightMargin:    Theme.AppTheme.spacingSm
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        text:           String(_row.modelData.title || "")
                        color:          _row._clickable ? Theme.AppTheme.accent : Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold:      true
                        elide:          Text.ElideRight
                    }

                    AppWidgets.StatusChip {
                        visible: _row._status.length > 0
                        status:  _row._status
                    }
                }

                Label {
                    Layout.fillWidth: true
                    visible:        String(_row.modelData.metaText || "").length > 0
                    text:           String(_row.modelData.metaText || "")
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    elide:          Text.ElideRight
                }
            }

            MouseArea {
                anchors.fill: parent
                enabled: _row._clickable
                cursorShape: _row._clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.itemActivated(_row.modelData)
            }
        }
    }
}
