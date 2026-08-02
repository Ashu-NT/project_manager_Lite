pragma ComponentBehavior: Bound
import QtQuick
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
    property string errorText:     ""

    signal composeRequested()
    signal replyRequested(var commentData)
    signal editRequested(var commentData)
    signal deleteRequested(var commentData)
    signal reactionRequested(var payload)
    signal reactionRemovalRequested(var payload)
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
            title:    "Discussion"
            subtitle: root._feedItems.length > 0 ? String(root._feedItems.length) : ""
            busy:     root.isBusy
            createLabel: root.canCompose ? "Post Update" : ""
            actions: [
                { id: "read",    label: "Mark Mentions Read", icon: "approve", enabled: root.selectedTaskId.length > 0, danger: false },
                { id: "refresh", label: "Refresh",   icon: "refresh", enabled: true,                          danger: false }
            ]
            onCreateRequested: root.composeRequested()
            onActionTriggered: function(actionId) {
                if      (actionId === "read")    root.markReadRequested(root.selectedTaskId)
                else if (actionId === "refresh") root.refreshRequested()
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: "danger"
            message: root.errorText
        }

        // ── Activity timeline ─────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            implicitHeight: threadContent.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: threadContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.EmptyState {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: Math.min(threadContent.width, 360)
                    visible: root._feedItems.length === 0
                    title: root.commentsModel.emptyState || "No discussion for this task."
                }

                Repeater {
                    model: root._feedItems

                    delegate: TaskCommentCard {
                        id: commentCard
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.leftMargin: Math.min(
                            Number((commentCard.modelData.state || {}).threadDepth || 0),
                            3
                        ) * 24
                        commentData: commentCard.modelData
                        isBusy: root.isBusy

                        onReplyRequested: function(item) { root.replyRequested(item) }
                        onEditRequested: function(item) { root.editRequested(item) }
                        onDeleteRequested: function(item) { root.deleteRequested(item) }
                        onReactionRequested: function(payload) { root.reactionRequested(payload) }
                        onReactionRemovalRequested: function(payload) {
                            root.reactionRemovalRequested(payload)
                        }
                    }
                }
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
                            Layout.preferredWidth: 6
                            Layout.preferredHeight: 6
                            radius: 3
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
