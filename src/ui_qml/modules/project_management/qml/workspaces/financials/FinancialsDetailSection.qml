import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var costDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property var cashflowModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerModel:   ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var sourceAnalyticsModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })
    property bool isBusy: false
    property var detailPage: null

    readonly property bool _hasCost: String(root.costDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        if (root._idx === 3) return _sec3.implicitHeight
        if (root._idx === 4) return _sec4.implicitHeight
        if (root._idx === 5) return _sec5.implicitHeight
        if (root._idx === 6) return _sec6.implicitHeight
        return _sec7.implicitHeight
    }

    implicitHeight: _activeSectionH

    function _sv(key) {
        const s = root.costDetail.state || {}
        return String(s[key] || "")
    }

    readonly property var _ledgerColumns: [
        { "key": "title",        "label": "Reference",     "flex": 2                    },
        { "key": "subtitle",     "label": "Source / Stage","flex": 1.5                  },
        { "key": "statusLabel",  "label": "Amount",        "flex": 0, "minWidth": 110   },
        { "key": "supportingText","label": "Task / Resource","flex": 1.5                },
        { "key": "metaText",     "label": "Date / Policy", "flex": 0, "minWidth": 130   }
    ]

    readonly property var _cashflowColumns: [
        { "key": "title",        "label": "Period",           "flex": 1                 },
        { "key": "statusLabel",  "label": "Forecast",         "flex": 0, "minWidth": 110 },
        { "key": "subtitle",     "label": "Planned / Committed","flex": 2               },
        { "key": "supportingText","label": "Actual / Exposure","flex": 2                }
    ]

    readonly property var _commitmentColumns: [
        { "key": "title",        "label": "Source",           "flex": 2                 },
        { "key": "statusLabel",  "label": "Exposure",         "flex": 0, "minWidth": 100 },
        { "key": "subtitle",     "label": "Planned / Forecast","flex": 2                },
        { "key": "supportingText","label": "Committed / Actual","flex": 2               }
    ]

    // ── Section 0: Budget ─────────────────────────────────────────────────
    Item {
        id: _sec0
        width: parent.width
        implicitHeight: _sec0Col.implicitHeight
        visible: root._idx === 0

        Column {
            id: _sec0Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Budget"
            }

            AppWidgets.EmptyState {
                width: parent.width
                visible: !root._hasCost
                title: "No cost item selected"
                message: root.costDetail.emptyState || "Select a cost item from the list to review its financial detail."
            }

            Item {
                width: parent.width
                implicitHeight: _budgetContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                visible: root._hasCost

                ColumnLayout {
                    id: _budgetContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        Repeater {
                            model: [
                                { "lbl": "Budget",    "val": root._sv("plannedAmountLabel")   },
                                { "lbl": "Committed", "val": root._sv("committedAmountLabel") },
                                { "lbl": "Actual",    "val": root._sv("actualAmountLabel")    },
                                { "lbl": "Cost Type", "val": root.costDetail.statusLabel || "" }
                            ]

                            delegate: ColumnLayout {
                                id: _budgetCell
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                Label {
                                    Layout.fillWidth: true
                                    text: String(_budgetCell.modelData.lbl)
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: String(_budgetCell.modelData.val)
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                    wrapMode: Text.NoWrap
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        Repeater {
                            model: [
                                { "lbl": "Task",     "val": root._sv("taskName")          },
                                { "lbl": "Date",     "val": root._sv("incurredDateLabel")  },
                                { "lbl": "Currency", "val": root._sv("currency")           },
                                { "lbl": "Version",  "val": root._sv("version")            }
                            ]

                            delegate: ColumnLayout {
                                id: _metaCell
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                Label {
                                    Layout.fillWidth: true
                                    text: String(_metaCell.modelData.lbl)
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: String(_metaCell.modelData.val) || "—"
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.NoWrap
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(root.costDetail.description || "").length > 0
                        text: root.costDetail.description || ""
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    // ── Section 1: Actuals ────────────────────────────────────────────────
    Item {
        id: _sec1
        width: parent.width
        implicitHeight: _sec1Col.implicitHeight
        visible: root._idx === 1

        Column {
            id: _sec1Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Actuals"
            }

            AppWidgets.EmptyState {
                width: parent.width
                visible: (root.ledgerModel.items || []).length === 0
                title: root.ledgerModel.emptyState || "No ledger entries"
                message: "No ledger entries are available for the selected project."
            }

            Item {
                width: parent.width
                height: 220
                visible: (root.ledgerModel.items || []).length > 0

                AppWidgets.DataTable {
                    anchors.fill: parent
                    columns: root._ledgerColumns
                    rows: root.ledgerModel.items || []
                    loading: root.isBusy
                    emptyText: root.ledgerModel.emptyState || "No ledger entries."
                    onSortRequested: function(key) {}
                }
            }
        }
    }

    // ── Section 2: Forecast ───────────────────────────────────────────────
    Item {
        id: _sec2
        width: parent.width
        implicitHeight: _sec2Col.implicitHeight
        visible: root._idx === 2

        Column {
            id: _sec2Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Forecast"
            }

            AppWidgets.EmptyState {
                width: parent.width
                visible: (root.cashflowModel.items || []).length === 0
                title: root.cashflowModel.emptyState || "No cashflow data"
                message: "No cashflow periods are available for the selected project."
            }

            Item {
                width: parent.width
                height: 220
                visible: (root.cashflowModel.items || []).length > 0

                AppWidgets.DataTable {
                    anchors.fill: parent
                    columns: root._cashflowColumns
                    rows: root.cashflowModel.items || []
                    loading: root.isBusy
                    emptyText: root.cashflowModel.emptyState || "No forecast periods."
                    onSortRequested: function(key) {}
                }
            }
        }
    }

    // ── Section 3: Commitments ────────────────────────────────────────────
    Item {
        id: _sec3
        width: parent.width
        implicitHeight: _sec3Col.implicitHeight
        visible: root._idx === 3

        Column {
            id: _sec3Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Commitments"
            }

            AppWidgets.EmptyState {
                width: parent.width
                visible: (root.sourceAnalyticsModel.items || []).length === 0
                title: root.sourceAnalyticsModel.emptyState || "No commitment data"
                message: "No source analytics are available for the selected project."
            }

            Item {
                width: parent.width
                height: 180
                visible: (root.sourceAnalyticsModel.items || []).length > 0

                AppWidgets.DataTable {
                    anchors.fill: parent
                    columns: root._commitmentColumns
                    rows: root.sourceAnalyticsModel.items || []
                    loading: root.isBusy
                    emptyText: root.sourceAnalyticsModel.emptyState || "No commitments."
                    onSortRequested: function(key) {}
                }
            }
        }
    }

    // ── Section 4: Invoices ───────────────────────────────────────────────
    Item {
        id: _sec4
        width: parent.width
        implicitHeight: _sec4Col.implicitHeight
        visible: root._idx === 4

        Column {
            id: _sec4Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Invoices"
            }

            AppWidgets.EmptyState {
                width: parent.width
                title: "No invoices"
                message: "Invoice management will be available in a future release."
            }
        }
    }

    // ── Section 5: Purchase Orders ────────────────────────────────────────
    Item {
        id: _sec5
        width: parent.width
        implicitHeight: _sec5Col.implicitHeight
        visible: root._idx === 5

        Column {
            id: _sec5Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Purchase Orders"
            }

            AppWidgets.EmptyState {
                width: parent.width
                title: "No purchase orders"
                message: "Purchase order tracking will be available in a future release."
            }
        }
    }

    // ── Section 6: Earned Value ───────────────────────────────────────────
    Item {
        id: _sec6
        width: parent.width
        implicitHeight: _sec6Col.implicitHeight
        visible: root._idx === 6

        Column {
            id: _sec6Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Earned Value"
            }

            AppWidgets.EmptyState {
                width: parent.width
                visible: (root.overviewModel.metrics || []).length === 0
                title: "No EV data"
                message: "Select a project to view budget health and financial exposure metrics."
            }

            Item {
                width: parent.width
                implicitHeight: _evGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                visible: (root.overviewModel.metrics || []).length > 0

                GridLayout {
                    id: _evGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.spacingMd
                    columns: 2
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingMd

                    Repeater {
                        model: root.overviewModel.metrics || []

                        delegate: Rectangle {
                            id: _evCard
                            required property var modelData
                            Layout.fillWidth: true
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surfaceAlt
                            implicitHeight: _evCardContent.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: _evCardContent
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingXs

                                Label {
                                    Layout.fillWidth: true
                                    text: String(_evCard.modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: String(_evCard.modelData.value || "—")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                }
                                Label {
                                    Layout.fillWidth: true
                                    visible: String(_evCard.modelData.supportingText || "").length > 0
                                    text: String(_evCard.modelData.supportingText || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Section 7: Activity ───────────────────────────────────────────────
    Item {
        id: _sec7
        width: parent.width
        implicitHeight: _sec7Col.implicitHeight
        visible: root._idx === 7

        Column {
            id: _sec7Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Activity"
            }

            Item {
                width: parent.width
                implicitHeight: _activityFeed.implicitHeight + Theme.AppTheme.spacingMd * 2

                AppWidgets.ActivityFeed {
                    id: _activityFeed
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.spacingMd
                    items: root.ledgerModel.items || []
                    emptyText: "No ledger activity recorded for the selected project."
                }
            }
        }
    }
}
