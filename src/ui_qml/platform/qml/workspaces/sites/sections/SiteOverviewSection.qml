pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Site Detail's Overview tab: Basic Information / Physical Address /
// Operational Context (main column) plus Key Statistics / Recent Activity
// (summary rail), then full-width Operational Calendar and Related Actions
// cards -- the same information architecture as Organization Overview
// (OrganizationOverviewSection.qml), specialized for Site's own business
// semantics (an operational location, not a second Organization). A
// presentational section only -- all data is supplied by the orchestrator
// (AdminSiteDetailPage.qml).
Column {
    id: root
    spacing: 0

    property var basicInfoFields: []
    property var addressFields: []
    property var operationalContextFields: []
    property var statistics: ({})
    property var relatedActions: []
    property var recentActivity: []
    property var calendarSummary: ({
        "hasCalendar": false, "calendarName": "", "source": "",
        "workingWeekLabel": "", "timeZone": "", "holidaySetLabel": ""
    })

    signal navigateToDestination(string destinationId)
    signal viewAllActivityRequested()
    signal manageCalendarRequested()

    readonly property var _calendarFields: root.calendarSummary.hasCalendar ? [
        { "label": "Effective Calendar", "value": String(root.calendarSummary.calendarName || "-") },
        { "label": "Source", "value": root.calendarSummary.source === "override" ? "Site override" : "Inherited from Organization" },
        { "label": "Working Week", "value": String(root.calendarSummary.workingWeekLabel || "-") },
        { "label": "Time Zone", "value": String(root.calendarSummary.timeZone || "-") },
        { "label": "Holiday Rules", "value": String(root.calendarSummary.holidaySetLabel || "-") }
    ] : []

    Item {
        width: root.width
        implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

        GridLayout {
            id: overviewGrid
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.AppTheme.spacingMd
            columns: root.width < 640 ? 1 : 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            // -- Main column: Basic Information / Physical Address /
            // Operational Context -- ~2/3 width on desktop; content-driven
            // height only, never a fixed/computed override that can
            // under-report a card's real height and get clipped by
            // SectionCard's own clip: true.
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
                                    text: String(modelData.value || "-")
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
                    title: "Physical Address"
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
                                    text: String(modelData.value || "-")
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
                    title: "Operational Context"
                    outlined: true

                    GridLayout {
                        id: contextGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingLg
                        rowSpacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root.operationalContextFields

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
                                    text: String(modelData.value || "-")
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }
            }

            // -- Summary rail: statistics + recent activity (~1/3 width)
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
                            label: "Departments"
                            value: String(root.statistics.departmentCount !== undefined ? root.statistics.departmentCount : "--")
                            clickable: true
                            onActivated: root.navigateToDestination("departments")
                        }
                        AppWidgets.OverviewMetricTile {
                            Layout.fillWidth: true
                            compact: true
                            label: "Employees"
                            value: String(root.statistics.employeeCount !== undefined ? root.statistics.employeeCount : "--")
                            clickable: true
                            onActivated: root.navigateToDestination("employees")
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
                            emptyText: "No activity yet. Business activity for this site will appear here."
                        }
                    }
                }
            }
        }
    }

    // -- Operational Calendar: this site's effective calendar (its own
    // override when assigned, otherwise the Organization's default) --
    // compact + read-only. Full editing (working rules, exceptions, shift
    // patterns) lives exclusively in Platform > Calendars; "Manage
    // Calendar" below routes to this site's own Calendar tab.
    Item {
        width: root.width
        implicitHeight: calendarCard.implicitHeight + Theme.AppTheme.spacingMd * 2

        AppWidgets.SectionCard {
            id: calendarCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.spacingMd
            title: "Operational Calendar"
            outlined: true

            ColumnLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: !root.calendarSummary.hasCalendar
                    text: "No calendar is configured for this site or its organization."
                    color: Theme.AppTheme.textMuted
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: root.calendarSummary.hasCalendar
                    columns: root.width < 420 ? 1 : (root.width < 760 ? 2 : 4)
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._calendarFields

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
                                text: String(modelData.value || "-")
                                color: Theme.AppTheme.textPrimary
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight
                    horizontalAlignment: Text.AlignRight
                    text: "Manage Calendar"
                    color: Theme.AppTheme.accent
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true

                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.manageCalendarRequested() }
                }
            }
        }
    }

    // -- Related Actions: full content width so its tiles get real room to
    // lay out horizontally instead of always falling back to a stack.
    // Departments/Employees are this site's own local tabs -- no Projects/
    // Documents tile since neither has a real scoped destination today
    // (see SiteProjectsSection.qml / SiteDocumentsSection.qml).
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
