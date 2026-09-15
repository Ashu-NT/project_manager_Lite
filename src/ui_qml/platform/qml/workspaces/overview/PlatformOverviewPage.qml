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

    // -- Lower row (two lists). "View all" is shown only when the caller
    // has already confirmed the underlying destination is accessible to
    // the current session -- this page never re-derives that itself. -----
    property var recentActivity: []
    property bool recentActivityViewAllAccessible: false
    signal recentActivityViewAllRequested()
    property var approvalActions: ({})
    property bool approvalActionsViewAllAccessible: false
    signal approvalActionsViewAllRequested()
    signal approvalActionActivated(int index)

    // -- Supporting summary: a single compact, full-width metric bar (not
    // a list-style card) -- each metric is individually navigable per its
    // own "clickable" flag, plus one explicit "View documents" link. ------
    property var documentsGlance: ({})
    property bool viewDocumentsAccessible: false
    signal viewDocumentsRequested()
    signal documentsMetricActivated(int index)

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

                            objectName: "overviewMetricTile_" + String(_tile.modelData.label || "")
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

                // -- Lower row: Recent Administrative Activity / Approvals & Actions.
                // GridLayout (not RowLayout + manual percentage widths) so
                // the two cards split evenly and reflow to a single stacked
                // column at narrow widths without a self-referential width
                // binding.
                GridLayout {
                    id: _lowerRow
                    Layout.fillWidth: true
                    visible: root.errorMessage.length === 0
                    columns: _content.width < 1000 ? 1 : 2
                    columnSpacing: Theme.AppTheme.sectionGap
                    rowSpacing: Theme.AppTheme.sectionGap

                    Rectangle {
                        Layout.fillWidth: true
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

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Recent Administrative Activity"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.sectionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    visible: root.recentActivityViewAllAccessible
                                    text: "View all"
                                    color: Theme.AppTheme.accent
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true

                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: root.recentActivityViewAllRequested() }
                                }
                            }

                            AppWidgets.ActivityFeed {
                                Layout.fillWidth: true
                                items: root.recentActivity
                                emptyText: "No recent administrative activity."
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
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

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Approvals & Actions"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.sectionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    visible: root.approvalActionsViewAllAccessible
                                    text: "View all"
                                    color: Theme.AppTheme.accent
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true

                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: root.approvalActionsViewAllRequested() }
                                }
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

                // -- Documents at a glance: one compact, full-width summary
                // bar -- a heading + a short row of metric tiles, not a
                // tall list-style card. Each metric tile is individually
                // navigable per its own "clickable" flag; "View documents"
                // is a separate explicit link to the Documents destination.
                Rectangle {
                    id: _documentsGlanceCard
                    Layout.fillWidth: true
                    visible: root.errorMessage.length === 0 && (root.documentsGlance.metrics || []).length > 0
                    implicitHeight: _documentsGlanceColumn.implicitHeight + Theme.AppTheme.marginLg * 2
                    radius: Theme.AppTheme.radiusLg
                    color: Theme.AppTheme.surfaceRaised
                    border.width: 1
                    border.color: Theme.AppTheme.subtleBorder

                    ColumnLayout {
                        id: _documentsGlanceColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginLg
                        spacing: Theme.AppTheme.spacingSm

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(root.documentsGlance.title || "Documents at a glance")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                visible: root.viewDocumentsAccessible
                                text: "View documents"
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true

                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: root.viewDocumentsRequested() }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingMd

                            Repeater {
                                model: root.documentsGlance.metrics || []

                                delegate: AppWidgets.OverviewMetricTile {
                                    id: _glanceTile
                                    required property var modelData
                                    required property int index

                                    Layout.preferredWidth: 220
                                    Layout.fillWidth: false
                                    compact: true
                                    label: String(_glanceTile.modelData.label || "")
                                    value: String(_glanceTile.modelData.value || "--")
                                    supportingText: String(_glanceTile.modelData.supportingText || "")
                                    clickable: _glanceTile.modelData.clickable === true
                                    onActivated: root.documentsMetricActivated(_glanceTile.index)
                                }
                            }

                            Item { Layout.fillWidth: true }
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
}
