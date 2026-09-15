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
// treatment specific to the Platform Overview landing page.
AppLayouts.WorkspaceFrame {
    id: root

    property bool isLoading: false
    property string errorMessage: ""
    property string emptyState: ""

    // -- KPI row (each metric carries its own real "clickable" flag,
    // already resolved against the Context Navigation Tree's accessible
    // destinations upstream -- never a blanket switch) --------------------
    property var metrics: []
    signal metricActivated(int index)

    // -- Summary row (3 cards; Organization Snapshot rows are individually
    // row-navigable per their own "clickable" flag, Access & Security and
    // Module & Tenant Status are informational) ---------------------------
    property var organizationSnapshot: ({})
    signal organizationRowActivated(int index)
    property var accessSecurity: ({})
    property var moduleTenantStatus: ({})

    // -- Lower row (two lists) --------------------------------------------
    property var recentActivity: []
    property var approvalActions: ({})
    signal approvalActionActivated(int index)

    // -- Supporting summary (single full-width, whole-card-clickable) -----
    property var documentsGlance: ({})
    signal documentsGlanceActivated()

    property string warningText: ""

    title: "Platform Overview"

    Item {
        anchors.fill: parent

        AppWidgets.LoadingOverlay {
            anchors.fill: parent
            loading: root.isLoading
            message: "Loading platform overview…"
            visible: root.isLoading
        }

        AppWidgets.EmptyState {
            anchors.centerIn: parent
            width: Math.min(parent.width, 360)
            visible: !root.isLoading && root.errorMessage.length === 0 && root.emptyState.length > 0
            title: root.emptyState
        }

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: _content.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            visible: !root.isLoading && root.emptyState.length === 0
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: _content
                width: parent.width
                spacing: Theme.AppTheme.sectionGap

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.errorMessage.length > 0
                    tone: "danger"
                    message: root.errorMessage
                }

                // -- KPI tiles ----------------------------------------------
                GridLayout {
                    Layout.fillWidth: true
                    visible: root.errorMessage.length === 0 && root.metrics.length > 0
                    columns: Math.max(1, Math.min(root.metrics.length, Math.floor(width / 176)))
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingMd

                    Repeater {
                        model: root.metrics

                        delegate: AppWidgets.OverviewMetricTile {
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
                            clickable: _tile.modelData.clickable === true
                            onActivated: root.metricActivated(_tile.index)
                        }
                    }
                }

                // -- Summary row: Organization Snapshot / Access & Security /
                // Module & Tenant Status --------------------------------------
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.sectionGap
                    visible: root.errorMessage.length === 0

                    OverviewCard {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        title: String(root.organizationSnapshot.title || "Organization Snapshot")
                        rows: root.organizationSnapshot.rows || []
                        emptyState: String(root.organizationSnapshot.emptyState || "")
                        rowsClickable: true
                        onRowActivated: function(index) { root.organizationRowActivated(index) }
                    }

                    OverviewCard {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        title: String(root.accessSecurity.title || "Access & Security")
                        rows: root.accessSecurity.rows || []
                        emptyState: String(root.accessSecurity.emptyState || "")
                    }

                    OverviewCard {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        title: String(root.moduleTenantStatus.title || "Module & Tenant Status")
                        rows: root.moduleTenantStatus.rows || []
                        emptyState: String(root.moduleTenantStatus.emptyState || "")
                    }
                }

                // -- Lower row: Recent Administrative Activity / Approvals & Actions --
                RowLayout {
                    id: _lowerRow
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.sectionGap
                    visible: root.errorMessage.length === 0

                    Rectangle {
                        Layout.preferredWidth: (_lowerRow.width - _lowerRow.spacing) * 0.45
                        Layout.alignment: Qt.AlignTop
                        implicitHeight: _activityColumn.implicitHeight + Theme.AppTheme.marginLg * 2
                        radius: Theme.AppTheme.radiusLg
                        color: Theme.AppTheme.surfaceRaised
                        border.width: 1
                        border.color: Theme.AppTheme.subtleBorder

                        ColumnLayout {
                            id: _activityColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.marginLg
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Recent Administrative Activity"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold: true
                            }

                            AppWidgets.ActivityFeed {
                                Layout.fillWidth: true
                                items: root.recentActivity
                                emptyText: "No recent administrative activity."
                            }
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: (_lowerRow.width - _lowerRow.spacing) * 0.55
                        Layout.alignment: Qt.AlignTop
                        implicitHeight: _approvalsColumn.implicitHeight + Theme.AppTheme.marginLg * 2
                        radius: Theme.AppTheme.radiusLg
                        color: Theme.AppTheme.surfaceRaised
                        border.width: 1
                        border.color: Theme.AppTheme.subtleBorder

                        ColumnLayout {
                            id: _approvalsColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.marginLg
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Approvals & Actions"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold: true
                            }

                            AppWidgets.ActivityFeed {
                                id: _approvalsFeed
                                Layout.fillWidth: true
                                rowsActivatable: true
                                emptyText: String(root.approvalActions.emptyState || "No approvals are awaiting a decision.")
                                items: {
                                    const source = root.approvalActions.items || []
                                    const mapped = []
                                    for (let i = 0; i < source.length; i += 1) {
                                        const item = source[i]
                                        const metaParts = [item.subtitle, item.metaText].filter(p => String(p || "").length > 0)
                                        mapped.push({
                                            title: item.title,
                                            statusLabel: item.statusLabel,
                                            metaText: metaParts.join(" · "),
                                            tone: String(item.statusLabel || "").toLowerCase() === "pending" ? "warning" : "neutral"
                                        })
                                    }
                                    return mapped
                                }
                                onItemActivated: function(item) {
                                    const source = root.approvalActions.items || []
                                    for (let i = 0; i < source.length; i += 1) {
                                        if (source[i].title === item.title && source[i].metaText === item.metaText) {
                                            root.approvalActionActivated(i)
                                            return
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // -- Documents at a glance (single, whole-card clickable) ------
                OverviewCard {
                    Layout.fillWidth: true
                    visible: root.errorMessage.length === 0 && (root.documentsGlance.rows || []).length > 0
                    title: String(root.documentsGlance.title || "Documents at a glance")
                    rows: root.documentsGlance.rows || []
                    emptyState: String(root.documentsGlance.emptyState || "")
                    clickable: true
                    onActivated: root.documentsGlanceActivated()
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
}
