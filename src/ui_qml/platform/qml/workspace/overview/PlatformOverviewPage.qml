pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

// Platform's own Overview page. Deliberately NOT a reskin of the shared
// App.Layouts.WorkspaceOverviewPage shell (still used as-is, untouched, so
// any future page that adopts it keeps today's plainer look until it opts
// into something like this) -- this is a bespoke, denser, more visual
// treatment specific to the Platform Overview landing page: individually
// elevated KPI tiles instead of one pill-strip, and "leaderboard row" style
// cards instead of stacked label/value/support columns.
AppLayouts.WorkspaceFrame {
    id: root

    // -- KPI row --------------------------------------------------------
    property var metrics: []
    property bool metricsClickable: false
    signal metricActivated(int index)

    // -- Highlight cards (small, curated call-outs) ----------------------
    property string highlightsHeading: "Access & Governance"
    property var highlightCards: []

    // -- Breakdown cards (larger, list-shaped detail) --------------------
    property string breakdownsHeading: "Workforce Breakdown"
    property var breakdownCards: []

    property string warningText: ""

    title: "Platform Overview"

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: _content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: _content
            width: parent.width
            spacing: Theme.AppTheme.sectionGap

            // -- KPI tiles ----------------------------------------------
            GridLayout {
                Layout.fillWidth: true
                visible: root.metrics.length > 0
                columns: Math.max(1, Math.min(root.metrics.length, Math.floor(width / 176)))
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: root.metrics

                    delegate: OverviewMetricTile {
                        id: _tile
                        required property var modelData
                        required property int index

                        Layout.fillWidth: true
                        label: String(_tile.modelData.label || "")
                        value: String(_tile.modelData.value || "--")
                        supportingText: String(_tile.modelData.supportingText || "")
                        trend: String(_tile.modelData.trend || "")
                        trendLabel: String(_tile.modelData.trendLabel || "")
                        colorHint: String(_tile.modelData.colorHint || "")
                        clickable: root.metricsClickable
                        onActivated: root.metricActivated(_tile.index)
                    }
                }
            }

            // -- Highlight cards ------------------------------------------
            AppControls.Label {
                Layout.fillWidth: true
                Layout.topMargin: Theme.AppTheme.spacingXs
                visible: root.highlightsHeading.length > 0 && root.highlightCards.length > 0
                text: root.highlightsHeading
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.typePageTitleSize
                font.bold: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.sectionGap
                visible: root.highlightCards.length > 0

                Repeater {
                    model: root.highlightCards

                    delegate: OverviewCard {
                        id: _highlight
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        title: String(_highlight.modelData.title || "")
                        rows: _highlight.modelData.rows || []
                        emptyState: String(_highlight.modelData.emptyState || "")
                    }
                }
            }

            // -- Breakdown cards --------------------------------------------
            AppControls.Label {
                Layout.fillWidth: true
                Layout.topMargin: Theme.AppTheme.spacingXs
                visible: root.breakdownsHeading.length > 0 && root.breakdownCards.length > 0
                text: root.breakdownsHeading
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.typePageTitleSize
                font.bold: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.sectionGap
                visible: root.breakdownCards.length > 0

                Repeater {
                    model: root.breakdownCards

                    delegate: OverviewCard {
                        id: _breakdown
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        title: String(_breakdown.modelData.title || "")
                        rows: _breakdown.modelData.rows || []
                        emptyState: String(_breakdown.modelData.emptyState || "Not yet available")
                    }
                }
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root.warningText.length > 0
                tone: "warning"
                message: root.warningText
            }

            Item { Layout.preferredHeight: Theme.AppTheme.spacingMd }
        }
    }
}
