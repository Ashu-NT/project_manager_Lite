pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var detailPage:          null
    property var heatmapItem:         null
    property var scenariosModel:      ({ "items": [] })
    property var dependenciesModel:   ({ "items": [] })
    property var intakeItemsModel:    ({ "items": [], "emptyState": "" })
    property var recentActionsModel:  ({ "items": [], "emptyState": "" })

    readonly property int  _idx:     root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property bool _hasItem: root.heatmapItem !== null
        && String(root.heatmapItem ? root.heatmapItem.id || "" : "").length > 0

    // Dynamic implicitHeight — only the active section contributes
    implicitHeight: _activeSectionH + Theme.AppTheme.spacingLg

    readonly property int _activeSectionH: {
        const i = root._idx
        if (i === 0) return _sec0.implicitHeight
        if (i === 1) return _sec1.implicitHeight
        if (i === 2) return _sec2.implicitHeight
        if (i === 3) return _sec3.implicitHeight
        return _sec4.implicitHeight
    }

    // ── Section container — sections stacked at same origin ───────────
    Item {
        id: _sectionArea
        anchors.top:   parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
        height: root._activeSectionH

        // ── Section 0: Overview ────────────────────────────────────────
        Item {
            id: _sec0
            visible: root._idx === 0
            width:          parent.width
            implicitHeight: Math.max(140, _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2)

            ColumnLayout {
                id: _overviewCol
                anchors.top:         parent.top
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                Label {
                    Layout.fillWidth: true
                    visible: !root._hasItem
                    text: "Select a project from the portfolio table to view delivery pressure, scenarios, and analysis."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Label {
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

                        Label {
                            text: "Delivery Pressure"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }

                        Label {
                            Layout.fillWidth: true
                            text: String(root.heatmapItem ? root.heatmapItem.statusLabel || "—" : "—")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Label {
                            text: "Late / Critical / Peak Util"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }

                        Label {
                            Layout.fillWidth: true
                            text: String(root.heatmapItem ? root.heatmapItem.supportingText || "—" : "—")
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

                        Label {
                            text: "Cost Variance"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }

                        Label {
                            Layout.fillWidth: true
                            text: String(root.heatmapItem ? root.heatmapItem.metaText || "—" : "—")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                        }
                    }
                }
            }
        }

        // ── Section 1: Scenarios ───────────────────────────────────────
        Item {
            id: _sec1
            visible: root._idx === 1
            width:          parent.width
            implicitHeight: Math.max(120, _sec1Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

            ColumnLayout {
                id: _sec1Col
                anchors.top:         parent.top
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                Label {
                    text: "SCENARIOS"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    font.letterSpacing: 0.5
                }

                Label {
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
                            anchors.left:   parent.left
                            anchors.right:  parent.right
                            anchors.top:    parent.top
                            anchors.margins: 8
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                Label {
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

                            Label {
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

                Label {
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

        // ── Section 2: Dependencies ────────────────────────────────────
        Item {
            id: _sec2
            visible: root._idx === 2
            width:          parent.width
            implicitHeight: Math.max(120, _sec2Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

            ColumnLayout {
                id: _sec2Col
                anchors.top:         parent.top
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                Label {
                    text: "DEPENDENCIES"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    font.letterSpacing: 0.5
                }

                Label {
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
                            anchors.left:   parent.left
                            anchors.right:  parent.right
                            anchors.top:    parent.top
                            anchors.margins: 8
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                Label {
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

                            Label {
                                Layout.fillWidth: true
                                text: String(_s2Row.modelData.subtitle || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide: Text.ElideRight
                            }

                            Label {
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

                Label {
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

        // ── Section 3: Funding ─────────────────────────────────────────
        Item {
            id: _sec3
            visible: root._idx === 3
            width:          parent.width
            implicitHeight: Math.max(120, _sec3Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

            ColumnLayout {
                id: _sec3Col
                anchors.top:         parent.top
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                Label {
                    text: "FUNDING"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    font.letterSpacing: 0.5
                }

                Label {
                    Layout.fillWidth: true
                    text: "Portfolio intake items — proposed work with budget and capacity demand."
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
                            anchors.left:   parent.left
                            anchors.right:  parent.right
                            anchors.top:    parent.top
                            anchors.margins: 8
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                Label {
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

                            Label {
                                Layout.fillWidth: true
                                text: String(_s3Row.modelData.subtitle || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide: Text.ElideRight
                            }

                            Label {
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

                Label {
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

        // ── Section 4: Activity ────────────────────────────────────────
        Item {
            id: _sec4
            visible: root._idx === 4
            width:          parent.width
            implicitHeight: Math.max(120, _sec4Col.implicitHeight + Theme.AppTheme.spacingMd * 2)

            ColumnLayout {
                id: _sec4Col
                anchors.top:         parent.top
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                Label {
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
