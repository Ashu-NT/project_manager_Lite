pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property var detailPage:    null
    property var fields:        []
    property var activityItems: []
    property string emptyState: "No details available."

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0

    implicitHeight: _sectionArea.implicitHeight + 2 * Theme.AppTheme.pagePadding
    width: parent ? parent.width : 0

    Item {
        id: _sectionArea
        anchors.top:         parent.top
        anchors.topMargin:   Theme.AppTheme.pagePadding
        anchors.left:        parent.left
        anchors.leftMargin:  Theme.AppTheme.pagePadding
        anchors.right:       parent.right
        anchors.rightMargin: Theme.AppTheme.pagePadding
        implicitHeight: _overview.visible ? _overview.implicitHeight
            : _activity.implicitHeight + Theme.AppTheme.spacingMd

        // ── Overview (fields grid) ────────────────────────────────────
        Item {
            id: _overview
            anchors.top:   parent.top
            anchors.left:  parent.left
            anchors.right: parent.right
            visible:        root._idx === 0
            implicitHeight: _fieldsGrid.visible ? _fieldsGrid.implicitHeight : _emptyState.implicitHeight

            GridLayout {
                id: _fieldsGrid
                width:         parent.width
                columns:       2
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing:    Theme.AppTheme.spacingMd
                visible:       root.fields.length > 0

                Repeater {
                    model: root.fields

                    delegate: ColumnLayout {
                        id: _fieldRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            text:           _fieldRow.modelData.label || ""
                            color:          Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.family:    Theme.AppTheme.fontFamily
                            font.bold:      true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text:           _fieldRow.modelData.value || "—"
                            color:          Theme.AppTheme.textPrimary
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.family:    Theme.AppTheme.fontFamily
                            wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }
                }
            }

            AppWidgets.EmptyState {
                id: _emptyState
                width:   parent.width
                visible: root.fields.length === 0
                title:   root.emptyState
            }
        }

        // ── Activity feed ─────────────────────────────────────────────
        AppWidgets.ActivityFeed {
            id: _activity
            anchors.top:   parent.top
            anchors.left:  parent.left
            anchors.right: parent.right
            visible:        root._idx === 1
            items:          root.activityItems
            emptyText:      "No activity recorded yet."
        }
    }
}
