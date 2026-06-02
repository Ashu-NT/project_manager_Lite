pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property var activityFeed: ({ items: [], emptyState: "No support activity recorded" })

    Layout.fillWidth: true
    spacing: 0

    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Support Activity" }

    Item {
        Layout.fillWidth:       true
        Layout.preferredHeight: 220

        ListView {
            id: _activityList
            anchors.fill:      parent
            anchors.topMargin: 4
            clip:              true
            boundsBehavior:    Flickable.StopAtBounds
            spacing:           0
            model:             root.activityFeed.items || []
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                id: _actRow
                required property var modelData
                required property int index
                width: ListView.view ? ListView.view.width : 0
                height: 44

                Rectangle {
                    id: _actDot
                    anchors.left: parent.left; anchors.leftMargin: Theme.AppTheme.marginMd; anchors.verticalCenter: parent.verticalCenter
                    width: 7; height: 7; radius: 4
                    color: {
                        const s = (_actRow.modelData.statusLabel || "").toLowerCase()
                        if (s.includes("export") || s.includes("success") || s.includes("approv") || s.includes("install")) return Theme.AppTheme.success
                        if (s.includes("error")  || s.includes("fail")    || s.includes("reject"))                          return Theme.AppTheme.danger
                        if (s.includes("warn"))                                                                              return Theme.AppTheme.warning
                        return Theme.AppTheme.textMuted
                    }
                }

                Rectangle {
                    visible: _actRow.index < (ListView.view ? ListView.view.count - 1 : 0)
                    anchors.horizontalCenter: _actDot.horizontalCenter
                    anchors.top:   _actDot.bottom; anchors.topMargin: 2; anchors.bottom: parent.bottom
                    width: 1; color: Theme.AppTheme.divider
                }

                ColumnLayout {
                    anchors { left: _actDot.right; leftMargin: Theme.AppTheme.spacingSm; right: parent.right; rightMargin: Theme.AppTheme.marginSm; verticalCenter: parent.verticalCenter }
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.AppTheme.spacingXs
                        AppControls.Label {
                            Layout.fillWidth: true
                            text:  _actRow.modelData.title || ""
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight
                        }
                        AppWidgets.StatusChip {
                            visible: (_actRow.modelData.statusLabel || "").length > 0
                            status:  _actRow.modelData.statusLabel || ""
                        }
                    }
                    AppControls.Label {
                        visible: (_actRow.modelData.metaText || "").length > 0
                        text:    _actRow.modelData.metaText || ""
                        color:   Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; elide: Text.ElideRight
                    }
                }
            }
        }

        AppWidgets.EmptyState {
            anchors.centerIn: parent
            width:   Math.min(_activityList.width, 240)
            visible: _activityList.count === 0
            title:   String(root.activityFeed.emptyState || "No support activity recorded")
        }
    }
}
