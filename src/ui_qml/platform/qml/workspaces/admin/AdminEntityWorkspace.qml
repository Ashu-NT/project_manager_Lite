import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// Reusable admin entity workspace: section title bar + TableToolbar + DataTable.
// All selected-record business actions live exclusively in the right detail panel.
ColumnLayout {
    id: root
    spacing: 0

    // ── Public API ────────────────────────────────────────────────
    property string sectionTitle:    ""
    property string entityLabel:     ""
    property var    catalog:         ({ items: [], emptyState: "No records" })
    property var    columns:         []
    property bool   isBusy:          false
    property bool   isLoading:       false
    property string errorMessage:    ""
    property string feedbackMessage: ""
    property string selectedRowId:   ""

    signal createRequested()
    signal rowSelected(string rowId)
    signal rowActivated(string rowId)
    signal refreshRequested()

    // ── Pagination state ──────────────────────────────────────────
    property int _pageSize:    50
    property int _currentPage: 0

    readonly property int _totalCount: (root.catalog.items || []).length
    readonly property int _pageCount:  Math.max(1, Math.ceil(root._totalCount / root._pageSize))
    readonly property var _pageRows:   (root.catalog.items || []).slice(
        root._currentPage * root._pageSize,
        (root._currentPage + 1) * root._pageSize
    )

    onCatalogChanged: root._currentPage = 0

    // ── Section title bar ─────────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        height: Theme.AppTheme.toolbarHeight - 6
        color:  Theme.AppTheme.surfaceRaised
        z:      1

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill:        parent
            anchors.leftMargin:  Theme.AppTheme.marginMd
            anchors.rightMargin: 8
            spacing:             Theme.AppTheme.spacingXs

            AppControls.Label {
                text:           root.sectionTitle
                color:          Theme.AppTheme.textPrimary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold:      true
            }

            AppControls.Label {
                visible:        (root.catalog.items || []).length > 0
                text:           String((root.catalog.items || []).length)
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                leftPadding:    4
            }

            Item { Layout.fillWidth: true }
        }
    }

    // ── Table toolbar (always visible) ────────────────────────────
    AppWidgets.TableToolbar {
        id: _tableToolbar
        Layout.fillWidth: true
        showCreate:    root.entityLabel.length > 0
        createLabel:   "New " + root.entityLabel
        showRefresh:   true
        showCustomize: root.columns.length > 0
        isBusy:        root.isBusy
        onCreateRequested:  root.createRequested()
        onRefreshRequested: root.refreshRequested()
        onCustomizeClicked: _dataTable.openColumnCustomizer(_tableToolbar.customizeButtonItem)
    }

    // ── Inline state banners ──────────────────────────────────────
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: (root.isLoading || root.isBusy) && root.errorMessage.length === 0
        tone:    "info"
        message: root.isBusy ? "Saving changes..." : "Loading..."
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.errorMessage.length > 0
        tone:    "danger"
        message: root.errorMessage
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
        tone:    "success"
        message: root.feedbackMessage
    }

    // ── Data table ────────────────────────────────────────────────
    AppWidgets.DataTable {
        id: _dataTable
        Layout.fillWidth:  true
        Layout.fillHeight: true

        rows:          root._pageRows
        columns:       root.columns
        emptyText:     root.catalog.emptyState || "No records"
        loading:       root.isLoading
        selectedRowId: root.selectedRowId

        onRowSelected:  function(rowId) { root.rowSelected(rowId)  }
        onRowActivated: function(rowId) { root.rowActivated(rowId) }
    }

    // ── Pagination footer ─────────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        height: 34
        color:  Theme.AppTheme.surfaceRaised

        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill:        parent
            anchors.leftMargin:  Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            spacing:             Theme.AppTheme.spacingSm

            AppControls.Label {
                text: {
                    if (root._totalCount === 0) return "No records"
                    const s = root._currentPage * root._pageSize + 1
                    const e = Math.min((root._currentPage + 1) * root._pageSize, root._totalCount)
                    return s + "–" + e + " of " + root._totalCount
                }
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            Item { Layout.fillWidth: true }

            AppControls.Label {
                text:           "Per page:"
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            Repeater {
                model: [25, 50, 100]
                delegate: Rectangle {
                    id: _pgSzBtn
                    required property int modelData
                    implicitWidth:  28; implicitHeight: 22; radius: 3
                    color: root._pageSize === _pgSzBtn.modelData
                        ? Theme.AppTheme.accent
                        : _pgSzMA.containsMouse ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surface
                    border.color: root._pageSize === _pgSzBtn.modelData
                        ? Theme.AppTheme.accent : Theme.AppTheme.divider
                    border.width: 1

                    AppControls.Label {
                        anchors.centerIn: parent
                        text:           String(_pgSzBtn.modelData)
                        color:          root._pageSize === _pgSzBtn.modelData
                            ? "white" : Theme.AppTheme.textSecondary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    MouseArea {
                        id: _pgSzMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape:  Qt.PointingHandCursor
                        onClicked: { root._pageSize = _pgSzBtn.modelData; root._currentPage = 0 }
                    }
                }
            }

            Rectangle {
                implicitWidth: 22; implicitHeight: 22; radius: 3
                color: _prevPageMA.containsMouse && root._currentPage > 0
                    ? Theme.AppTheme.hoverSurface : "transparent"
                border.color: Theme.AppTheme.divider; border.width: 1
                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name: "chevron_left"; size: 10
                    iconColor: root._currentPage > 0
                        ? Theme.AppTheme.textSecondary : Theme.AppTheme.divider
                }
                MouseArea {
                    id: _prevPageMA
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: root._currentPage > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                    enabled: root._currentPage > 0
                    onClicked: root._currentPage -= 1
                }
            }

            AppControls.Label {
                text:           (root._currentPage + 1) + " / " + root._pageCount
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            Rectangle {
                implicitWidth: 22; implicitHeight: 22; radius: 3
                color: _nextPageMA.containsMouse && root._currentPage < root._pageCount - 1
                    ? Theme.AppTheme.hoverSurface : "transparent"
                border.color: Theme.AppTheme.divider; border.width: 1
                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name: "chevron_right"; size: 10
                    iconColor: root._currentPage < root._pageCount - 1
                        ? Theme.AppTheme.textSecondary : Theme.AppTheme.divider
                }
                MouseArea {
                    id: _nextPageMA
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: root._currentPage < root._pageCount - 1
                        ? Qt.PointingHandCursor : Qt.ArrowCursor
                    enabled: root._currentPage < root._pageCount - 1
                    onClicked: root._currentPage += 1
                }
            }
        }
    }
}
