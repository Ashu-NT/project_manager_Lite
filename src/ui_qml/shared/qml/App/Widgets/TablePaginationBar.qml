pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    // ── Public API ────────────────────────────────────────────────────
    property int currentPage:      1
    property int pageSize:         25
    property int totalItems:       0
    property var pageSizeOptions:  [25, 50, 100]
    property bool busy:            false

    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)

    // ── Private computed ──────────────────────────────────────────────
    readonly property int _totalPages: Math.max(1, Math.ceil(totalItems / Math.max(1, pageSize)))
    readonly property int _pageStart:  totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1
    readonly property int _pageEnd:    Math.min(currentPage * pageSize, totalItems)

    implicitHeight: 36
    color:          Theme.AppTheme.surfaceAlt

    Rectangle {
        anchors.top:   parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
        height: 1
        color:  Theme.AppTheme.divider
    }

    RowLayout {
        anchors.fill:        parent
        anchors.leftMargin:  Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        // ── Rows per page ─────────────────────────────────────────────
        RowLayout {
            spacing: Theme.AppTheme.spacingXs

            Label {
                text:           "Rows per page:"
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            ComboBox {
                id: _pageSizeBox
                model:         root.pageSizeOptions
                enabled:       !root.busy
                implicitWidth: 64
                implicitHeight: 26
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize

                currentIndex: {
                    for (let i = 0; i < root.pageSizeOptions.length; i++) {
                        if (root.pageSizeOptions[i] === root.pageSize) return i
                    }
                    return 0
                }

                onActivated: function(idx) {
                    root.pageSizeRequested(root.pageSizeOptions[idx])
                }
            }
        }

        Item { Layout.fillWidth: true }

        // ── Showing X–Y of Z ──────────────────────────────────────────
        Label {
            text: root.totalItems === 0
                ? "No records"
                : "Showing " + root._pageStart + "–" + root._pageEnd + " of " + root.totalItems
            color:          Theme.AppTheme.textMuted
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        // ── Prev / Next ───────────────────────────────────────────────
        RowLayout {
            spacing: Theme.AppTheme.spacingXs

            Rectangle {
                id: _prevBtn
                implicitWidth:  64
                implicitHeight: 26
                radius:         Theme.AppTheme.radiusSm
                readonly property bool _disabled: root.busy || root.currentPage <= 1
                color: _prevHover.containsMouse && !_prevBtn._disabled
                    ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surfaceOverlay

                Label {
                    anchors.centerIn: parent
                    text:           "‹ Prev"
                    color:          _prevBtn._disabled
                        ? Theme.AppTheme.textMuted : Theme.AppTheme.textSecondary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold:      !_prevBtn._disabled
                }
                MouseArea {
                    id: _prevHover
                    anchors.fill:  parent
                    hoverEnabled:  true
                    cursorShape:   _prevBtn._disabled ? Qt.ArrowCursor : Qt.PointingHandCursor
                    enabled:       !_prevBtn._disabled
                    onClicked:     root.pageRequested(root.currentPage - 1)
                }
            }

            Rectangle {
                id: _nextBtn
                implicitWidth:  64
                implicitHeight: 26
                radius:         Theme.AppTheme.radiusSm
                readonly property bool _disabled: root.busy || root.currentPage >= root._totalPages
                color: _nextHover.containsMouse && !_nextBtn._disabled
                    ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surfaceOverlay

                Label {
                    anchors.centerIn: parent
                    text:           "Next ›"
                    color:          _nextBtn._disabled
                        ? Theme.AppTheme.textMuted : Theme.AppTheme.textSecondary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold:      !_nextBtn._disabled
                }
                MouseArea {
                    id: _nextHover
                    anchors.fill:  parent
                    hoverEnabled:  true
                    cursorShape:   _nextBtn._disabled ? Qt.ArrowCursor : Qt.PointingHandCursor
                    enabled:       !_nextBtn._disabled
                    onClicked:     root.pageRequested(root.currentPage + 1)
                }
            }
        }
    }
}
