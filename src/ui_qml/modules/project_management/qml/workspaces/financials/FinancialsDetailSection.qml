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

    implicitHeight: _mainCol.implicitHeight

    readonly property bool _hasCost: String(root.costDetail.id || "").length > 0
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

    Column {
        id: _mainCol
        width: parent.width
        spacing: 0

        // ── Section 0: Budget ─────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }

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

                // ── Primary financial amounts (compact 4-col) ────────
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

                // ── Secondary metadata (compact 4-col) ──────────────
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    Repeater {
                        model: [
                            { "lbl": "Task",     "val": root._sv("taskName")         },
                            { "lbl": "Date",     "val": root._sv("incurredDateLabel") },
                            { "lbl": "Currency", "val": root._sv("currency")          },
                            { "lbl": "Version",  "val": root._sv("version")           }
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

                // ── Description ──────────────────────────────────────
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

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 1: Actuals ────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }

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

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 2: Forecast ───────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }

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

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 3: Commitments ────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 3; detailPage: root.detailPage }

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

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 4: Invoices ───────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 4; detailPage: root.detailPage }

        AppWidgets.SectionHeading {
            width: parent.width
            label: "Invoices"
        }

        AppWidgets.EmptyState {
            width: parent.width
            title: "No invoices"
            message: "Invoice management will be available in a future release."
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 5: Purchase Orders ────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 5; detailPage: root.detailPage }

        AppWidgets.SectionHeading {
            width: parent.width
            label: "Purchase Orders"
        }

        AppWidgets.EmptyState {
            width: parent.width
            title: "No purchase orders"
            message: "Purchase order tracking will be available in a future release."
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 6: Earned Value ───────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 6; detailPage: root.detailPage }

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

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.AppTheme.divider
        }

        // ── Section 7: Activity ───────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 7; detailPage: root.detailPage }

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
