pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var    commentsModel:  AppMock.MockFactory.catalog()
    property var    presenceModel:  AppMock.MockFactory.catalog()
    property string selectedTaskId: ""
    property bool   isBusy:        false
    property bool   canCompose:    false

    signal composeRequested()
    signal markReadRequested(string taskId)
    signal refreshRequested()

    readonly property var _feedItems: root.commentsModel.items || []
    readonly property var _presence:  root.presenceModel.items  || []

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left:  parent.left
        anchors.right: parent.right
        anchors.top:   parent.top
        spacing: 0

        // ── Section toolbar ───────────────────────────────────────────
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title:    "Activity"
            subtitle: root._feedItems.length > 0 ? String(root._feedItems.length) : ""
            busy:     root.isBusy
            createLabel: root.canCompose ? "Post Update" : ""
            actions: [
                { id: "read",    label: "Mark Read", icon: "approve", enabled: root.selectedTaskId.length > 0, danger: false },
                { id: "refresh", label: "Refresh",   icon: "refresh", enabled: true,                          danger: false }
            ]
            onCreateRequested: root.composeRequested()
            onActionTriggered: function(actionId) {
                if      (actionId === "read")    root.markReadRequested(root.selectedTaskId)
                else if (actionId === "refresh") root.refreshRequested()
            }
        }

        // ── Activity timeline ─────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            implicitHeight: _feed.implicitHeight + Theme.AppTheme.spacingMd * 2

            AppWidgets.ActivityFeed {
                id: _feed
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.top:         parent.top
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                items:     root._feedItems
                emptyText: root.commentsModel.emptyState || "No activity for this task."
            }
        }

        // ── Active presence ───────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            implicitHeight: _presenceContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            visible: root._presence.length > 0

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Theme.AppTheme.divider
            }

            ColumnLayout {
                id: _presenceContent
                anchors.left:    parent.left
                anchors.right:   parent.right
                anchors.top:     parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing:         Theme.AppTheme.spacingXs

                AppControls.Label {
                    text:           "ACTIVE PRESENCE"
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold:      true
                    font.letterSpacing: 0.8
                }

                Repeater {
                    model: root._presence
                    delegate: RowLayout {
                        id: _pRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: Theme.AppTheme.success
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text:           String(_pRow.modelData.title || "")
                            color:          Theme.AppTheme.textSecondary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            elide:          Text.ElideRight
                        }

                        AppControls.Label {
                            text:           String(_pRow.modelData.metaText || "")
                            color:          Theme.AppTheme.textMuted
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                    }
                }
            }
        }
    }
}
