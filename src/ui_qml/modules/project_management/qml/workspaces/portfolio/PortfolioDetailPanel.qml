pragma ComponentBehavior: Bound
import App.Controls 1.0 as AppControls

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var detailPage: null
    property var heatmapItem: null
    property var scenariosModel: ({ "items": [] })
    property var dependenciesModel: ({ "items": [] })
    property var intakeItemsModel: ({ "items": [], "emptyState": "" })
    property var recentActionsModel: ({ "items": [], "emptyState": "" })

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property bool _hasItem: root.heatmapItem !== null
        && String(root.heatmapItem ? root.heatmapItem.id || "" : "").length > 0
    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        if (root._idx === 3) return _sec3.implicitHeight
        return _sec4.implicitHeight
    }

    implicitHeight: _activeSectionH + Theme.AppTheme.spacingLg
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        sourceComponent: Component {
            Item {
                width: parent ? parent.width : 0
                implicitHeight: Math.max(140, _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2)

                ColumnLayout {
                    id: _overviewCol
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingMd

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: !root._hasItem
                        text: "Select a project from the portfolio table to view delivery pressure, scenarios, and analysis."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: root._hasItem
                        text: String(root.heatmapItem ? root.heatmapItem.title || "" : "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.titleSize
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        visible: root._hasItem
                        spacing: Theme.AppTheme.spacingSm

                        AppWidgets.StatusChip {
                            status: String(root.heatmapItem ? root.heatmapItem.subtitle || "" : "")
                        }

                        AppWidgets.StatusChip {
                            status: String(root.heatmapItem ? root.heatmapItem.statusLabel || "" : "")
                        }
                    }

                    Rectangle {
                        visible: root._hasItem
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.AppTheme.divider
                    }

                    GridLayout {
                        visible: root._hasItem
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            AppControls.Label {
                                text: "Delivery Pressure"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.heatmapItem ? root.heatmapItem.statusLabel || "-" : "-")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            AppControls.Label {
                                text: "Late / Critical / Peak Util"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.heatmapItem ? root.heatmapItem.supportingText || "-" : "-")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            AppControls.Label {
                                text: "Cost Variance"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.heatmapItem ? root.heatmapItem.metaText || "-" : "-")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 1
        sourceComponent: Component {
            Item {
                width: parent ? parent.width : 0
                implicitHeight: Math.max(120, _sec1Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

                ColumnLayout {
                    id: _sec1Col
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        text: "SCENARIOS"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        font.letterSpacing: 0.5
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "What-if portfolios that include this project in their selection."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: {
                            const pid = root.heatmapItem ? String(root.heatmapItem.id || "") : ""
                            if (!pid) return []
                            return (root.scenariosModel.items || []).filter(function(s) {
                                const ids = (s.state || {}).projectIds || []
                                return ids.indexOf(pid) >= 0
                            })
                        }

                        delegate: Rectangle {
                            id: _s1Row
                            required property var modelData

                            Layout.fillWidth: true
                            height: _s1RowLayout.implicitHeight + 16
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceAlt
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1

                            ColumnLayout {
                                id: _s1RowLayout
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 8
                                spacing: 2

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_s1Row.modelData.title || "")
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    AppWidgets.StatusChip {
                                        status: String(_s1Row.modelData.statusLabel || "")
                                    }
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_s1Row.modelData.subtitle || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: {
                            const pid = root.heatmapItem ? String(root.heatmapItem.id || "") : ""
                            if (!pid) return true
                            return (root.scenariosModel.items || []).filter(function(s) {
                                return ((s.state || {}).projectIds || []).indexOf(pid) >= 0
                            }).length === 0
                        }
                        text: "This project is not included in any saved scenarios."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        sourceComponent: Component {
            Item {
                width: parent ? parent.width : 0
                implicitHeight: Math.max(120, _sec2Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

                ColumnLayout {
                    id: _sec2Col
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        text: "DEPENDENCIES"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        font.letterSpacing: 0.5
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Cross-project links where this project is predecessor or successor."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: {
                            const pid = root.heatmapItem ? String(root.heatmapItem.id || "") : ""
                            if (!pid) return []
                            return (root.dependenciesModel.items || []).filter(function(d) {
                                const s = d.state || {}
                                return s.predecessorProjectId === pid || s.successorProjectId === pid
                            })
                        }

                        delegate: Rectangle {
                            id: _s2Row
                            required property var modelData

                            Layout.fillWidth: true
                            height: _s2RowLayout.implicitHeight + 16
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceAlt
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1

                            ColumnLayout {
                                id: _s2RowLayout
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 8
                                spacing: 2

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_s2Row.modelData.title || "")
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    AppWidgets.StatusChip {
                                        status: String(_s2Row.modelData.statusLabel || "")
                                    }
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_s2Row.modelData.subtitle || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide: Text.ElideRight
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_s2Row.modelData.supportingText || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: {
                            const pid = root.heatmapItem ? String(root.heatmapItem.id || "") : ""
                            if (!pid) return true
                            return (root.dependenciesModel.items || []).filter(function(d) {
                                const s = d.state || {}
                                return s.predecessorProjectId === pid || s.successorProjectId === pid
                            }).length === 0
                        }
                        text: "No cross-project dependencies recorded for this project."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 3
        sourceComponent: Component {
            Item {
                width: parent ? parent.width : 0
                implicitHeight: Math.max(120, _sec3Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

                ColumnLayout {
                    id: _sec3Col
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        text: "FUNDING"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        font.letterSpacing: 0.5
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Portfolio intake items - proposed work with budget and capacity demand."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.intakeItemsModel.items || []

                        delegate: Rectangle {
                            id: _s3Row
                            required property var modelData

                            Layout.fillWidth: true
                            height: _s3RowLayout.implicitHeight + 16
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceAlt
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1

                            ColumnLayout {
                                id: _s3RowLayout
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 8
                                spacing: 2

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_s3Row.modelData.title || "")
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    AppWidgets.StatusChip {
                                        status: String(_s3Row.modelData.statusLabel || "")
                                    }
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_s3Row.modelData.subtitle || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide: Text.ElideRight
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_s3Row.modelData.supportingText || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: (root.intakeItemsModel.items || []).length === 0
                        text: root.intakeItemsModel.emptyState || "No intake items are available yet."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 4
        sourceComponent: Component {
            Item {
                width: parent ? parent.width : 0
                implicitHeight: Math.max(120, _sec4Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

                ColumnLayout {
                    id: _sec4Col
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        text: "ACTIVITY"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        font.letterSpacing: 0.5
                    }

                    AppWidgets.ActivityFeed {
                        Layout.fillWidth: true
                        items: {
                            const projectName = root.heatmapItem
                                ? String(root.heatmapItem.title || "")
                                : ""
                            const all = root.recentActionsModel.items || []
                            if (!projectName) return all.map(function(item) {
                                return {
                                    "title": String(item.title || ""),
                                    "metaText": String(item.metaText || item.subtitle || ""),
                                    "statusLabel": String(item.statusLabel || "")
                                }
                            })
                            return all
                                .filter(function(item) {
                                    return String(item.statusLabel || "") === projectName
                                })
                                .map(function(item) {
                                    return {
                                        "title": String(item.title || ""),
                                        "metaText": String(item.metaText || item.subtitle || ""),
                                        "statusLabel": String(item.statusLabel || "")
                                    }
                                })
                        }
                        emptyText: "No recent activity found for this project."
                    }
                }
            }
        }
    }
}
