pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var collection: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property bool busy: false
    property bool selectable: false
    property string selectedId: ""
    readonly property var _items: root.collection.items || []
    signal pageRequested(int page)
    signal itemSelected(string itemId)

    implicitHeight: _column.implicitHeight

    ColumnLayout {
        id: _column
        width: parent.width
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.collection.title || ""
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.sectionTitleSize
                    font.bold: true
                }
                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.collection.subtitle || ""
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppControls.Label {
                text: String(Number(root.collection.total || 0) > 0
                    ? Number(root.collection.total) : root._items.length)
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root._items.length === 0
            title: "No records"
            message: root.collection.emptyState || "No records are available."
        }

        Column {
            Layout.fillWidth: true
            visible: root._items.length > 0
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: root._items

                delegate: Rectangle {
                    id: _row
                    required property var modelData
                    required property int index
                    width: parent ? parent.width : 0
                    implicitHeight: _rowContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    radius: Theme.AppTheme.radiusSm
                    color: root.selectable && String(_row.modelData.id || "") === root.selectedId
                        ? Theme.AppTheme.accentSoft
                        : _row.index % 2 === 0
                        ? Theme.AppTheme.surfaceAlt
                        : Theme.AppTheme.surfaceRaised
                    border.width: root.selectable && String(_row.modelData.id || "") === root.selectedId ? 2 : 1
                    border.color: root.selectable && String(_row.modelData.id || "") === root.selectedId
                        ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder

                    TapHandler {
                        enabled: root.selectable
                        onTapped: root.itemSelected(String(_row.modelData.id || ""))
                    }

                    RowLayout {
                        id: _rowContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_row.modelData.title || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_row.modelData.subtitle || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_row.modelData.supportingText || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        ColumnLayout {
                            Layout.alignment: Qt.AlignTop
                            Layout.maximumWidth: 250
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.alignment: Qt.AlignRight
                                text: String(_row.modelData.statusLabel || "")
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            AppControls.Label {
                                Layout.maximumWidth: 250
                                text: String(_row.modelData.metaText || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                horizontalAlignment: Text.AlignRight
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }


        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.collection.total || 0) > Number(root.collection.pageSize || 50)
            currentPage: Number(root.collection.page || 1)
            pageSize: Number(root.collection.pageSize || 50)
            totalItems: Number(root.collection.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.pageRequested(page) }
        }
    }
}
