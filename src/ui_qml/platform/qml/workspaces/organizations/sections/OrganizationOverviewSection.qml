pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Organization Detail's Overview tab: Basic Information / Registered
// Address / Contact (main column) plus Key Statistics / Recent Activity /
// Related Actions (summary rail + full-width tile row). A presentational
// section only -- all data and the isDestinationAccessible check are
// supplied by the orchestrator (AdminOrganizationDetailPage.qml).
Column {
    id: root
    spacing: 0

    property var basicInfoFields: []
    property var addressFields: []
    property var contactFields: []
    property var statistics: ({})
    property var relatedActions: []
    property var recentActivity: []
    property var isDestinationAccessible: function(_destinationId) { return false }

    signal navigateToDestination(string destinationId)
    signal viewAllActivityRequested()

    Item {
        width: root.width
        implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

        GridLayout {
            id: overviewGrid
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.AppTheme.spacingMd
            // root.width is the section CONTENT column, already net of the
            // shell/platform/detail-page nav rails -- not the window width.
            // 640 keeps both 1600x1000 and 1366x768 desktop breakpoints
            // two-column while a ~1000px window (content ~290px) still stacks.
            columns: root.width < 640 ? 1 : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            // -- Main column: Basic Information / Registered Address / Contact
            // ~2/3 width on desktop; content-driven height only -- never a
            // fixed/computed override that can under-report a card's real
            // height and get clipped by SectionCard's own clip: true.
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? Math.round(overviewGrid.width * 0.66)
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Basic Information"
                    outlined: true

                    GridLayout {
                        id: basicInfoGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.basicInfoFields

                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.value || "—")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Registered Address"
                    outlined: true

                    GridLayout {
                        id: addressGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.addressFields

                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.value || "—")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Contact Information"
                    outlined: true

                    GridLayout {
                        id: contactGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.contactFields

                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(modelData.value || "—")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }
            }

            // -- Summary rail: statistics + activity + actions (~1/3 width)
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: overviewGrid.columns === 2
                    ? overviewGrid.width - Math.round(overviewGrid.width * 0.66) - overviewGrid.columnSpacing
                    : overviewGrid.width
                Layout.alignment: Qt.AlignTop
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Key Statistics"
                    outlined: true

                    GridLayout {
                        id: statsGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingSm
                        rowSpacing: Theme.AppTheme.spacingSm

                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Sites"
                            value: String(root.statistics.siteCount !== undefined ? root.statistics.siteCount : "--")
                            clickable: root.isDestinationAccessible("sites")
                            onActivated: root.navigateToDestination("sites")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Departments"
                            value: String(root.statistics.departmentCount !== undefined ? root.statistics.departmentCount : "--")
                            clickable: root.isDestinationAccessible("departments")
                            onActivated: root.navigateToDestination("departments")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Employees"
                            value: String(root.statistics.employeeCount !== undefined ? root.statistics.employeeCount : "--")
                            clickable: root.isDestinationAccessible("employees")
                            onActivated: root.navigateToDestination("employees")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Documents"
                            value: String(root.statistics.documentCount !== undefined ? root.statistics.documentCount : "--")
                            clickable: root.isDestinationAccessible("documents")
                            onActivated: root.navigateToDestination("documents")
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Recent Activity"
                    outlined: true

                    ColumnLayout {
                        id: activityColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.alignment: Qt.AlignRight
                            visible: (root.recentActivity || []).length > 0
                            text: "View all"
                            color: Theme.AppTheme.accent
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true

                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.viewAllActivityRequested() }
                        }

                        AppWidgets.ActivityFeed {
                            Layout.fillWidth: true
                            items: root.recentActivity || []
                            emptyText: "No recent administrative activity for this organization."
                        }
                    }
                }
            }
        }
    }

    // -- Related Actions: full content width (not confined to the ~1/3
    // summary rail) so its tiles get real room to lay out horizontally
    // instead of always falling back to a stack.
    Item {
        width: root.width
        implicitHeight: root.relatedActions.length > 0
            ? relatedActionsCard.implicitHeight + Theme.AppTheme.spacingMd * 2
            : 0
        visible: root.relatedActions.length > 0

        AppWidgets.SectionCard {
            id: relatedActionsCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.spacingMd
            title: "Related Actions"
            outlined: true

            GridLayout {
                id: actionsGrid
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.marginMd
                columnSpacing: Theme.AppTheme.spacingSm
                rowSpacing: Theme.AppTheme.spacingSm
                // Responsive tiling driven by the card's own available width
                // (a container query, not a window breakpoint): one row if
                // every tile fits at its minimum readable width, else a
                // 2-column wrap, else a single column.
                readonly property int _minTileWidth: 150
                readonly property int _actionCount: root.relatedActions.length
                columns: {
                    if (actionsGrid._actionCount <= 1) return 1
                    const perRow = Math.max(
                        1,
                        Math.floor(
                            (actionsGrid.width + actionsGrid.columnSpacing)
                            / (actionsGrid._minTileWidth + actionsGrid.columnSpacing)
                        )
                    )
                    if (perRow >= actionsGrid._actionCount) return actionsGrid._actionCount
                    return perRow >= 2 ? 2 : 1
                }

                Repeater {
                    model: root.relatedActions

                    delegate: AppWidgets.ActionTile {
                        required property var modelData
                        Layout.fillWidth: true

                        label: String(modelData.label || "")
                        iconName: String(modelData.icon || "")

                        onActivated: root.navigateToDestination(String(modelData.id || ""))
                    }
                }
            }
        }
    }
}
