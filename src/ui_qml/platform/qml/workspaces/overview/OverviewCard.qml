pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// Modern replacement for App.Widgets.OverviewSectionCard, scoped to
// Platform Overview only -- label/support on the left, the value emphasized
// on the right (a scannable "leaderboard row" shape), on an elevated card.
// Left as a Platform-local component rather than editing the shared widget,
// since OverviewSectionCard is still used as-is elsewhere.
Rectangle {
    id: root

    property string title: ""
    property string emptyState: ""
    property var rows: []
    // Whole-card navigation (e.g. "Documents at a glance" -> Documents).
    property bool clickable: false
    signal activated()
    // Per-row navigation (e.g. Organization Snapshot rows -> their own
    // Platform destination). Independent of `clickable` -- a card uses one
    // mode or the other, never both.
    property bool rowsClickable: false
    signal rowActivated(int index)

    implicitHeight: _layout.implicitHeight + Theme.AppTheme.marginLg * 2
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceRaised
    border.width: root.clickable && root.activeFocus ? 2 : 1
    border.color: (root.clickable && (root.activeFocus || _cardHover.hovered))
        ? Theme.AppTheme.accent
        : Theme.AppTheme.subtleBorder

    Behavior on border.color { ColorAnimation { duration: 120 } }

    activeFocusOnTab: root.clickable
    Accessible.role: root.clickable ? Accessible.Button : Accessible.Pane
    Accessible.name: root.clickable ? root.title : ""
    Accessible.onPressAction: if (root.clickable) root.activated()

    Keys.onPressed: (event) => {
        if (!root.clickable) {
            return
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            root.activated()
            event.accepted = true
        }
    }

    HoverHandler {
        id: _cardHover
        enabled: root.clickable
        cursorShape: root.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    TapHandler {
        enabled: root.clickable
        onTapped: root.activated()
    }

    ColumnLayout {
        id: _layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.AppTheme.spacingXs
            text: root.title
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.sectionSize
            font.bold: true
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.rows.length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.rows

            delegate: Rectangle {
                id: _rowWrap
                required property var modelData
                required property int index

                // `root.rowsClickable` enables the per-row-navigation mode
                // for this card; each row may still individually opt out
                // via `modelData.clickable === false` (e.g. a destination
                // the current user cannot access) -- never a blanket switch
                // that would expose an inaccessible destination as if it
                // were navigable.
                readonly property bool _clickable: root.rowsClickable && _rowWrap.modelData.clickable !== false

                Layout.fillWidth: true
                implicitHeight: _rowLayout.implicitHeight
                radius: Theme.AppTheme.radiusSm
                color: (_rowWrap._clickable && (_rowWrap.activeFocus || _rowHover.hovered))
                    ? Theme.AppTheme.hoverSurface
                    : "transparent"

                activeFocusOnTab: _rowWrap._clickable
                Accessible.role: _rowWrap._clickable ? Accessible.Button : Accessible.StaticText
                Accessible.name: _rowWrap._clickable
                    ? (String(_rowWrap.modelData.label || "") + ", " + String(_rowWrap.modelData.value || ""))
                    : ""
                Accessible.onPressAction: if (_rowWrap._clickable) root.rowActivated(_rowWrap.index)

                Keys.onPressed: (event) => {
                    if (!_rowWrap._clickable) {
                        return
                    }
                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                        root.rowActivated(_rowWrap.index)
                        event.accepted = true
                    }
                }

                HoverHandler {
                    id: _rowHover
                    enabled: _rowWrap._clickable
                    cursorShape: _rowWrap._clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
                }

                TapHandler {
                    enabled: _rowWrap._clickable
                    onTapped: root.rowActivated(_rowWrap.index)
                }

                ColumnLayout {
                    id: _rowLayout
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: root.rowsClickable ? Theme.AppTheme.spacingXs : 0
                    spacing: Theme.AppTheme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_rowWrap.modelData.label || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                elide: Text.ElideRight
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: String(_rowWrap.modelData.supportingText || "") !== ""
                                text: String(_rowWrap.modelData.supportingText || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide: Text.ElideRight
                            }
                        }

                        AppControls.Label {
                            text: String(_rowWrap.modelData.value || "")
                            color: Theme.AppTheme.accent
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.sectionSize
                            font.bold: true
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.AppTheme.spacingXs
                        height: 1
                        color: Theme.AppTheme.divider
                        visible: _rowWrap.index < root.rows.length - 1
                    }
                }
            }
        }
    }
}
