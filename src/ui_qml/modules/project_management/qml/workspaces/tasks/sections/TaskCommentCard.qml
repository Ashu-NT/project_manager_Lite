pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var commentData: ({})
    property bool isBusy: false

    signal replyRequested(var commentData)
    signal editRequested(var commentData)
    signal deleteRequested(var commentData)
    signal reactionRequested(var payload)
    signal reactionRemovalRequested(var payload)

    readonly property var _state: root.commentData.state || ({})
    readonly property var _reactions: root._state.reactions || []
    readonly property bool _isDeleted: Boolean(root._state.isDeleted)

    implicitHeight: content.implicitHeight + Theme.AppTheme.marginMd * 2
    radius: Theme.AppTheme.radiusMd
    color: root._isDeleted ? Theme.AppTheme.surfaceAlt : Theme.AppTheme.surfaceRaised
    border.color: root._state.isReply
        ? Theme.AppTheme.borderStrong
        : Theme.AppTheme.subtleBorder
    border.width: 1

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Rectangle {
                Layout.preferredWidth: 30
                Layout.preferredHeight: 30
                radius: 15
                color: root._isDeleted
                    ? Theme.AppTheme.surfaceSunken
                    : Theme.AppTheme.accentSoft

                AppControls.Label {
                    anchors.centerIn: parent
                    text: {
                        const author = String(root.commentData.title || "").replace("@", "")
                        return author.length > 0 ? author.charAt(0).toUpperCase() : "?"
                    }
                    color: root._isDeleted
                        ? Theme.AppTheme.textMuted
                        : Theme.AppTheme.accent
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.smallSize
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(root.commentData.title || "Unknown user")
                        color: Theme.AppTheme.textPrimary
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.smallSize
                        elide: Text.ElideRight
                    }

                    AppWidgets.StatusChip {
                        visible: root._isDeleted
                        status: "Deleted"
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: {
                        const parentAuthor = String(root._state.parentAuthorUsername || "")
                        const replyContext = parentAuthor.length > 0
                            ? "Reply to @" + parentAuthor + " | "
                            : ""
                        return replyContext + String(root.commentData.metaText || "")
                    }
                    color: Theme.AppTheme.textMuted
                    font.pixelSize: Theme.AppTheme.captionSize
                    elide: Text.ElideRight
                }
            }
        }

        AppControls.Label {
            Layout.fillWidth: true
            text: String(root.commentData.subtitle || "")
            color: root._isDeleted
                ? Theme.AppTheme.textMuted
                : Theme.AppTheme.textPrimary
            font.pixelSize: Theme.AppTheme.bodySize
            font.italic: root._isDeleted
            wrapMode: Text.WordWrap
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs
            visible: root._reactions.length > 0

            Repeater {
                model: root._reactions

                delegate: AppControls.SecondaryButton {
                    id: reactionChip
                    required property var modelData

                    implicitHeight: 28
                    implicitWidth: reactionLabel.implicitWidth + 18
                    enabled: !root.isBusy && Boolean(root._state.canReact)

                    contentItem: AppControls.Label {
                        id: reactionLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        text: String(reactionChip.modelData.emoji || "")
                            + " " + String(reactionChip.modelData.count || 0)
                        color: reactionChip.modelData.reactedByCurrentUser
                            ? Theme.AppTheme.accent
                            : Theme.AppTheme.textSecondary
                        font.bold: Boolean(reactionChip.modelData.reactedByCurrentUser)
                        font.pixelSize: Theme.AppTheme.smallSize
                    }

                    background: Rectangle {
                        radius: 14
                        color: reactionChip.modelData.reactedByCurrentUser
                            ? Theme.AppTheme.accentSoft
                            : Theme.AppTheme.surfaceAlt
                        border.color: reactionChip.modelData.reactedByCurrentUser
                            ? Theme.AppTheme.accent
                            : Theme.AppTheme.subtleBorder
                        border.width: 1
                    }

                    onClicked: {
                        const payload = {
                            "commentId": String(root._state.commentId || root.commentData.id || ""),
                            "emoji": String(reactionChip.modelData.emoji || "")
                        }
                        if (reactionChip.modelData.reactedByCurrentUser) {
                            root.reactionRemovalRequested(payload)
                        } else {
                            root.reactionRequested(payload)
                        }
                    }
                }
            }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: (root._state.attachments || []).length > 0
                || (root._state.linkedDocuments || []).length > 0
            text: {
                const parts = []
                const attachments = root._state.attachments || []
                const documents = root._state.linkedDocuments || []
                if (attachments.length > 0) parts.push("Attachments: " + attachments.join(", "))
                if (documents.length > 0) parts.push("Linked: " + documents.join(", "))
                return parts.join(" | ")
            }
            color: Theme.AppTheme.textSecondary
            font.pixelSize: Theme.AppTheme.captionSize
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs
            visible: Boolean(root._state.canReply)
                || Boolean(root._state.canEdit)
                || Boolean(root._state.canDelete)
                || Boolean(root._state.canReact)

            AppControls.SecondaryButton {
                visible: Boolean(root._state.canReply)
                implicitWidth: 78
                text: "Reply"
                iconName: "collaboration"
                enabled: !root.isBusy
                onClicked: root.replyRequested(root.commentData)
            }

            AppControls.SecondaryButton {
                visible: Boolean(root._state.canEdit)
                implicitWidth: 72
                text: "Edit"
                iconName: "edit"
                enabled: !root.isBusy
                onClicked: root.editRequested(root.commentData)
            }

            AppControls.SecondaryButton {
                id: reactButton
                visible: Boolean(root._state.canReact)
                implicitWidth: 82
                text: "React"
                iconName: "collaboration"
                enabled: !root.isBusy
                onClicked: reactionPicker.open()
            }

            Item { Layout.fillWidth: true }

            AppControls.Label {
                visible: Number(root._state.replyCount || 0) > 0
                text: String(root._state.replyCount) + (Number(root._state.replyCount) === 1 ? " reply" : " replies")
                color: Theme.AppTheme.textMuted
                font.pixelSize: Theme.AppTheme.captionSize
            }

            AppControls.SecondaryButton {
                visible: Boolean(root._state.canDelete)
                implicitWidth: 82
                text: "Delete"
                iconName: "delete"
                danger: true
                enabled: !root.isBusy
                onClicked: root.deleteRequested(root.commentData)
            }
        }
    }

    AppWidgets.AnchoredPopup {
        id: reactionPicker
        anchorItem: reactButton
        placement: "below-left"
        width: 258
        padding: Theme.AppTheme.marginSm
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1
        }

        contentItem: RowLayout {
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: ["\uD83D\uDC4D", "\u2764\uFE0F", "\uD83D\uDC40", "\uD83C\uDF89", "\u2705"]

                delegate: AppControls.SecondaryButton {
                    id: pickerButton
                    required property string modelData

                    implicitWidth: 42
                    implicitHeight: 36
                    text: pickerButton.modelData

                    contentItem: AppControls.Label {
                        text: pickerButton.text
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: Theme.AppTheme.sectionSize
                    }

                    background: Rectangle {
                        radius: Theme.AppTheme.radiusSm
                        color: pickerButton.hovered
                            ? Theme.AppTheme.hoverSurface
                            : Theme.AppTheme.surfaceRaised
                        border.color: pickerButton.activeFocus
                            ? Theme.AppTheme.focusBorder
                            : Theme.AppTheme.subtleBorder
                        border.width: 1
                    }

                    onClicked: {
                        root.reactionRequested({
                            "commentId": String(root._state.commentId || root.commentData.id || ""),
                            "emoji": pickerButton.modelData
                        })
                        reactionPicker.close()
                    }
                }
            }
        }
    }
}
