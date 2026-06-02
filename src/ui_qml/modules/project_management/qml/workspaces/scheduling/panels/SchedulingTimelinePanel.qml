pragma ComponentBehavior: Bound
import App.Controls 1.0 as AppControls

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import "../components"

SchedulingPanelFrame {
    id: root

    property var timelineModel: ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })

    readonly property var _items: root.timelineModel.items || []
    readonly property int _windowDays: {
        if (root._items.length === 0) {
            return 1
        }
        const firstState = root._items[0].state || {}
        return Math.max(1, parseInt(firstState.windowDays || 1, 10))
    }
    readonly property int _currentOffset: {
        if (root._items.length === 0) {
            return -1
        }
        const firstState = root._items[0].state || {}
        return parseInt(firstState.currentOffsetDays || -1, 10)
    }
    readonly property string _windowStartLabel: {
        if (root._items.length === 0) {
            return ""
        }
        return String((root._items[0].state || {}).windowStartLabel || "")
    }
    readonly property string _windowFinishLabel: {
        if (root._items.length === 0) {
            return ""
        }
        return String((root._items[0].state || {}).windowFinishLabel || "")
    }

    title: root.timelineModel.title || "Timeline"
    subtitle: root.timelineModel.subtitle || "Planning lane"

    function _barLeft(state, laneWidth) {
        const offset = Math.max(0, parseInt(state.startOffsetDays || 0, 10))
        return Math.round((offset / Math.max(1, root._windowDays)) * laneWidth)
    }

    function _barWidth(state, laneWidth) {
        const span = Math.max(1, parseInt(state.spanDays || 1, 10))
        return Math.max(
            state.milestone ? 12 : 18,
            Math.round((span / Math.max(1, root._windowDays)) * laneWidth)
        )
    }

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true
        implicitHeight: 320

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    text: root._windowStartLabel || "Window start"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }

                Item {
                    Layout.fillWidth: true
                }

                AppControls.Label {
                    visible: root._windowStartLabel.length > 0 && root._windowFinishLabel.length > 0
                    text: "Today marker"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }

                AppControls.Label {
                    text: root._windowFinishLabel || "Window finish"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.AppTheme.divider
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                AppControls.Label {
                    anchors.centerIn: parent
                    visible: root._items.length === 0
                    text: root.timelineModel.emptyState || "No timeline activities are available."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                ListView {
                    id: _timelineList
                    anchors.fill: parent
                    visible: root._items.length > 0
                    model: root._items
                    clip: true
                    spacing: Theme.AppTheme.spacingXs

                    delegate: Item {
                        id: _row

                        required property var modelData

                        width: _timelineList.width
                        height: 28

                        readonly property var _state: modelData.state || ({})

                        RowLayout {
                            anchors.fill: parent
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.preferredWidth: 110
                                text: String(_row.modelData.title || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide: Text.ElideRight
                            }

                            Item {
                                id: _laneHost
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true

                                Repeater {
                                    model: 8

                                    delegate: Rectangle {
                                        required property int index
                                        readonly property real _step: _laneHost.width / 8
                                        x: Math.round(index * _step)
                                        width: 1
                                        height: _laneHost.height
                                        color: Theme.AppTheme.divider
                                        opacity: 0.45
                                    }
                                }

                                Rectangle {
                                    visible: root._currentOffset >= 0 && root._currentOffset <= root._windowDays
                                    x: Math.round((root._currentOffset / Math.max(1, root._windowDays)) * _laneHost.width)
                                    width: 2
                                    height: _laneHost.height
                                    color: Theme.AppTheme.warning
                                    opacity: 0.9
                                }

                                Rectangle {
                                    visible: Boolean(_row._state.baselinePlaceholder)
                                    x: root._barLeft(_row._state, _laneHost.width)
                                    y: Math.round((_laneHost.height - 10) / 2)
                                    width: root._barWidth(_row._state, _laneHost.width)
                                    height: 10
                                    radius: 5
                                    color: Qt.rgba(0, 0, 0, 0)
                                    border.color: Theme.AppTheme.subtleBorder
                                    border.width: 1
                                    opacity: 0.6
                                }

                                Rectangle {
                                    x: root._barLeft(_row._state, _laneHost.width)
                                    y: Math.round((_laneHost.height - (_row._state.milestone ? 12 : 14)) / 2)
                                    width: root._barWidth(_row._state, _laneHost.width)
                                    height: _row._state.milestone ? 12 : 14
                                    radius: _row._state.milestone ? 6 : 4
                                    color: _row._state.critical
                                        ? Theme.AppTheme.danger
                                        : Theme.AppTheme.accent

                                    Rectangle {
                                        visible: !_row._state.milestone
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.bottom: parent.bottom
                                        width: Math.max(
                                            6,
                                            Math.round(parent.width * (Math.max(0, Math.min(100, Number(_row._state.progressPercent || 0))) / 100))
                                        )
                                        radius: parent.radius
                                        color: Theme.AppTheme.success
                                        opacity: 0.45
                                    }
                                }
                            }

                            AppControls.Label {
                                Layout.preferredWidth: 64
                                horizontalAlignment: Text.AlignRight
                                text: String(_row.modelData.statusLabel || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }
}
