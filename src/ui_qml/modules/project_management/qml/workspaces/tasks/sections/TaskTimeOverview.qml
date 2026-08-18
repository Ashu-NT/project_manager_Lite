pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // Task-scoped planned/actual/remaining/overrun totals plus the
    // per-resource breakdown, straight from TaskTimeSummaryDesktopDto
    // (docs §44 Time redesign) -- rendered as-is, never recalculated here.
    property var taskTimeSummary: ({ "hasSummary": false })
    property bool isBusy: false

    signal logTimeRequested()
    signal viewAssignmentRequested(string assignmentId)

    readonly property var _summary: root.taskTimeSummary || {}
    readonly property bool _hasSummary: root._summary.hasSummary === true
    readonly property var _rows: root._summary.resourceBreakdown || []
    readonly property bool _hasActual: root._hasSummary
        && String(root._summary.actualHoursLabel || "0.0 h").indexOf("0.0") !== 0

    Layout.fillWidth: true
    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingLg
            visible: !root._hasSummary
            title: "No time has been logged for this task yet."
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root._hasSummary
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                text: "Resource Breakdown"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Planned vs. actual execution by resource -- for allocation, capacity, and planning, see the Assignment section."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }

            // A small, fixed-size (one row per assignment) breakdown table
            // reads best as a lightweight Repeater grid rather than the
            // shared DataTable -- DataTable's virtualized/sortable/paged
            // machinery pays for itself on Time Entries below, not here.
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: _breakdownCol.implicitHeight + Theme.AppTheme.marginMd * 2
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceRaised
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1
                visible: root._rows.length > 0

                ColumnLayout {
                    id: _breakdownCol
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.bottomMargin: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 2
                            text: "Resource"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignRight
                            text: "Planned"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignRight
                            text: "Actual"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignRight
                            text: "Remaining / Overrun"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        Item { Layout.preferredWidth: 90 }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                        color: Theme.AppTheme.divider
                    }

                    Repeater {
                        model: root._rows

                        delegate: ColumnLayout {
                            id: _rowRoot
                            required property var modelData

                            Layout.fillWidth: true
                            spacing: 0

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: Theme.AppTheme.spacingSm
                                Layout.bottomMargin: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 2
                                    text: String(_rowRoot.modelData.resourceName || "")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    elide: Text.ElideRight
                                }
                                AppControls.Label {
                                    Layout.preferredWidth: 1
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                    text: String(_rowRoot.modelData.plannedHoursLabel || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                                AppControls.Label {
                                    Layout.preferredWidth: 1
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                    text: String(_rowRoot.modelData.actualHoursLabel || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                                AppControls.Label {
                                    Layout.preferredWidth: 1
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                    text: _rowRoot.modelData.hasOverrun
                                        ? String(_rowRoot.modelData.overrunHoursLabel || "") + " over"
                                        : String(_rowRoot.modelData.remainingHoursLabel || "")
                                    color: _rowRoot.modelData.hasOverrun ? Theme.AppTheme.danger : Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: _rowRoot.modelData.hasOverrun
                                }
                                Item {
                                    Layout.preferredWidth: 90
                                    implicitHeight: _viewAssignmentBtn.implicitHeight

                                    AppControls.SecondaryButton {
                                        id: _viewAssignmentBtn
                                        anchors.right: parent.right
                                        text: "View"
                                        onClicked: root.viewAssignmentRequested(
                                            String(_rowRoot.modelData.assignmentId || "")
                                        )
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                                color: Theme.AppTheme.divider
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 2
                            text: "TOTAL"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignRight
                            text: String(root._summary.plannedHoursLabel || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignRight
                            text: String(root._summary.actualHoursLabel || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignRight
                            text: root._summary.hasOverrun
                                ? String(root._summary.overrunHoursLabel || "") + " over"
                                : String(root._summary.remainingHoursLabel || "")
                            color: root._summary.hasOverrun ? Theme.AppTheme.danger : Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                        Item { Layout.preferredWidth: 90 }
                    }
                }
            }

            AppControls.PrimaryButton {
                Layout.alignment: Qt.AlignLeft
                Layout.topMargin: Theme.AppTheme.spacingSm
                visible: root._hasSummary && !root._hasActual
                text: "Log Time"
                iconName: "add"
                onClicked: root.logTimeRequested()
            }
        }
    }
}
