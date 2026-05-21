import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectDetail: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property bool isBusy: false
    property var detailPage: null

    signal editRequested()
    signal statusRequested()
    signal deleteRequested()

    function _sv(key) {
        const s = root.projectDetail.state || {}
        return String(s[key] || "")
    }

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0
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

    // ── Section 0: Overview ───────────────────────────────────────────────
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
                label: "Overview"
            }

            Item {
                width: parent.width
                implicitHeight: _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                ColumnLayout {
                    id: _overviewCol
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.spacingMd
                    anchors.rightMargin: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingMd

                    AppWidgets.EmptyState {
                        Layout.fillWidth: true
                        visible: !root._hasProject
                        title: "No project selected"
                        message: root.projectDetail.emptyState
                            || "Select a project from the catalog to review details or edit its setup."
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root._hasProject
                        spacing: Theme.AppTheme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Client"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("clientName") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide: Text.ElideRight
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Contact"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("clientContact") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide: Text.ElideRight
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Start"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("startDateLabel") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Finish"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("endDateLabel") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        visible: root._hasProject
                        color: Theme.AppTheme.divider
                        opacity: 0.5
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root._hasProject
                        spacing: Theme.AppTheme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Budget"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("plannedBudgetLabel") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Currency"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("currency") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Status"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            AppWidgets.StatusChip {
                                status: root.projectDetail.statusLabel || ""
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Version"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("version") ? "v" + root._sv("version") : "—"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: root._hasProject
                        text: root.projectDetail.description
                            || "No project description has been added yet."
                        color: String(root.projectDetail.description || "").length > 0
                            ? Theme.AppTheme.textSecondary
                            : Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                        maximumLineCount: 4
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    // ── Section 1: Schedule ───────────────────────────────────────────────
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
                label: "Schedule"
            }

            Item {
                width: parent.width
                implicitHeight: _scheduleContent.implicitHeight + Theme.AppTheme.spacingMd * 2

                ColumnLayout {
                    id: _scheduleContent
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.spacingMd
                    anchors.rightMargin: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingXs

                    AppWidgets.EmptyState {
                        Layout.fillWidth: true
                        visible: !root._hasProject
                        title: "No schedule data"
                        message: "Select a project to review its schedule."
                    }

                    Item {
                        Layout.fillWidth: true
                        visible: root._hasProject
                        implicitHeight: _scheduleGrid.implicitHeight

                        GridLayout {
                            id: _scheduleGrid
                            width: parent.width
                            columns: 2
                            columnSpacing: Theme.AppTheme.spacingMd
                            rowSpacing: Theme.AppTheme.spacingXs

                            Label {
                                text: "Start Date"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("startDateLabel") || "Not scheduled"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }

                            Label {
                                text: "Finish Date"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("endDateLabel") || "Not scheduled"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Section 2: Tasks ─────────────────────────────────────────────────
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
                label: "Tasks"
            }

            Item {
                width: parent.width
                implicitHeight: _tasksEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2

                AppWidgets.EmptyState {
                    id: _tasksEmpty
                    anchors.top: parent.top
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                    title: "Task execution data"
                    message: "Open the Tasks workspace to view delivery tasks assigned to this project."
                }
            }
        }
    }

    // ── Section 3: Resources ─────────────────────────────────────────────
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
                label: "Resources"
            }

            Item {
                width: parent.width
                implicitHeight: _resourcesEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2

                AppWidgets.EmptyState {
                    id: _resourcesEmpty
                    anchors.top: parent.top
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                    title: "Resource allocation data"
                    message: "Open the Resources workspace to review staffing and capacity assigned to this project."
                }
            }
        }
    }

    // ── Section 4: Financials ────────────────────────────────────────────
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
                label: "Financials"
            }

            Item {
                width: parent.width
                implicitHeight: _financialsCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                ColumnLayout {
                    id: _financialsCol
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.spacingMd
                    anchors.rightMargin: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingMd

                    AppWidgets.EmptyState {
                        Layout.fillWidth: true
                        visible: !root._hasProject
                        title: "No financial data"
                        message: "Select a project to review its financial information."
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root._hasProject
                        spacing: Theme.AppTheme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Planned Budget"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("plannedBudgetLabel") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: "Currency"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root._sv("currency") || "—"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }

                        Item { Layout.fillWidth: true }
                        Item { Layout.fillWidth: true }
                    }

                    AppWidgets.EmptyState {
                        Layout.fillWidth: true
                        visible: root._hasProject
                        title: "Cost tracking data"
                        message: "Open the Financials workspace to review actuals, commitments, and forecast against this project's budget."
                    }
                }
            }
        }
    }

    // ── Section 5: Risks ─────────────────────────────────────────────────
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
                label: "Risks"
            }

            Item {
                width: parent.width
                implicitHeight: _risksEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2

                AppWidgets.EmptyState {
                    id: _risksEmpty
                    anchors.top: parent.top
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                    title: "Risk register"
                    message: "Open the Register workspace to view risks, issues, and change requests tracked against this project."
                }
            }
        }
    }

    // ── Section 6: Documents ─────────────────────────────────────────────
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
                label: "Documents"
            }

            Item {
                width: parent.width
                implicitHeight: _documentsEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2

                AppWidgets.EmptyState {
                    id: _documentsEmpty
                    anchors.top: parent.top
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                    title: "Project documents"
                    message: "Document management is not yet configured for this project."
                }
            }
        }
    }

    // ── Section 7: Activity ──────────────────────────────────────────────
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
                implicitHeight: Math.max(_activityFeed.implicitHeight, 80) + Theme.AppTheme.spacingMd * 2

                AppWidgets.ActivityFeed {
                    id: _activityFeed
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.topMargin: Theme.AppTheme.spacingMd
                    anchors.leftMargin: Theme.AppTheme.spacingMd
                    anchors.rightMargin: Theme.AppTheme.spacingMd
                    items: {
                        const s = root.projectDetail.state || {}
                        return s.activityItems || []
                    }
                    emptyText: "No project activity recorded"
                }
            }
        }
    }
}
