import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property bool isItemsView: true
    property var itemDetail: ({ "fields": [], "linkedDocuments": [], "emptyState": "", "state": {} })
    property var categoryDetail: ({ "fields": [], "emptyState": "", "state": {} })
    property var detailPage: null
    property bool isBusy: false
    property var activityItems: []

    signal linkDocumentRequested()
    signal unlinkDocumentRequested(var documentData)

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _detail: root.isItemsView ? root.itemDetail : root.categoryDetail
    readonly property var _fields: root._detail ? (root._detail.fields || []) : []
    readonly property var _docs: root.isItemsView && root.itemDetail
        ? (root.itemDetail.linkedDocuments || []) : []

    width: parent ? parent.width : 0
    implicitHeight: _sectionArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

    Item {
        id: _sectionArea
        anchors.top: parent.top
        anchors.topMargin: Theme.AppTheme.pagePadding
        anchors.left: parent.left
        anchors.leftMargin: Theme.AppTheme.pagePadding
        anchors.right: parent.right
        anchors.rightMargin: Theme.AppTheme.pagePadding
        implicitHeight: _overviewPanel.visible ? _overviewPanel.implicitHeight
            : _documentsPanel.visible ? _documentsPanel.implicitHeight
            : _activityFeed.implicitHeight + Theme.AppTheme.spacingMd

        // ── Overview (section 0) ───────────────────────────────────
        Item {
            id: _overviewPanel
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            visible: root._idx === 0
            implicitHeight: _fieldsGrid.visible ? _fieldsGrid.implicitHeight : _overviewEmpty.implicitHeight

            GridLayout {
                id: _fieldsGrid
                width: parent.width
                columns: 2
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingMd
                visible: root._fields.length > 0

                Repeater {
                    model: root._fields

                    delegate: ColumnLayout {
                        id: _fd
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            text: _fd.modelData.label || ""
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.family: Theme.AppTheme.fontFamily
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: _fd.modelData.value || "—"
                            color: Theme.AppTheme.textPrimary
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.family: Theme.AppTheme.fontFamily
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: String(_fd.modelData.supportingText || "").length > 0
                            text: _fd.modelData.supportingText || ""
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.family: Theme.AppTheme.fontFamily
                        }
                    }
                }
            }

            AppWidgets.EmptyState {
                id: _overviewEmpty
                width: parent.width
                visible: root._fields.length === 0
                title: root._detail ? (root._detail.emptyState || "No details available.") : "No details available."
            }
        }

        // ── Documents (section 1, items only) ─────────────────────
        Item {
            id: _documentsPanel
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            visible: root.isItemsView && root._idx === 1
            implicitHeight: _docsLayout.implicitHeight

            ColumnLayout {
                id: _docsLayout
                width: parent.width
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Linked Documents"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.sectionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textPrimary
                    }

                    AppControls.SecondaryButton {
                        text: "Link Document"
                        iconName: "link"
                        enabled: !root.isBusy
                        onClicked: root.linkDocumentRequested()
                    }
                }

                Repeater {
                    model: root._docs

                    delegate: Rectangle {
                        id: _dr
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: _drRow.implicitHeight + Theme.AppTheme.spacingMd
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceRaised
                        border.color: Theme.AppTheme.divider
                        border.width: 1

                        RowLayout {
                            id: _drRow
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: Theme.AppTheme.marginMd
                            anchors.rightMargin: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: _dr.modelData.label || ""
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.family: Theme.AppTheme.fontFamily
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    visible: String(_dr.modelData.supportingText || "").length > 0
                                    text: _dr.modelData.supportingText || ""
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.family: Theme.AppTheme.fontFamily
                                }
                            }

                            AppControls.SecondaryButton {
                                text: "Unlink"
                                iconName: "unlink"
                                danger: true
                                enabled: !root.isBusy
                                onClicked: root.unlinkDocumentRequested(_dr.modelData)
                            }
                        }
                    }
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._docs.length === 0
                    title: "No documents linked to this item."
                }
            }
        }

        // ── Activity (items: section 2, categories: section 1) ────
        AppWidgets.ActivityFeed {
            id: _activityFeed
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            visible: root.isItemsView ? root._idx === 2 : root._idx === 1
            items: root.activityItems || []
            emptyText: "No activity recorded yet."
        }
    }
}
