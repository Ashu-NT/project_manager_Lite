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

    implicitHeight: _mainCol.implicitHeight

    function _sv(key) {
        const s = root.projectDetail.state || {}
        return String(s[key] || "")
    }

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0

    Column {
        id: _mainCol
        width: parent.width
        spacing: 0

        // ── Section 0: Overview ───────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Overview" }

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

                // ── Empty state when no project is selected ──
                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasProject
                    title: "No project selected"
                    message: root.projectDetail.emptyState
                        || "Select a project from the catalog to review details or edit its setup."
                }

                // ── Compact 4-column metadata panel ──────────────────────
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

                // ── Project description ───────────────────────────────────
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

        // ── Section 1: Schedule ───────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Schedule" }

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

        // ── Section 2: Tasks ─────────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Tasks" }

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

        // ── Section 3: Resources ─────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 3; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Resources" }

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

        // ── Section 4: Financials ────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 4; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Financials" }

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

                // Budget KPI summary
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

        // ── Section 5: Risks ─────────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 5; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Risks" }

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

        // ── Section 6: Documents ─────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 6; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Documents" }

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

        // ── Section 7: Activity ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 7; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Activity" }

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
