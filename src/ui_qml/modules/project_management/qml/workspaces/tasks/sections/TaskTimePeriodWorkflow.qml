pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var assignmentSummary: ({})
    property string selectedPeriodStart: ""
    property bool isBusy: false

    signal submitRequested(var payload)
    signal lockRequested(var payload)
    signal unlockRequested(var payload)

    readonly property var _state: root.assignmentSummary.state || {}
    readonly property var _summaryFields: root.assignmentSummary.fields || []
    readonly property bool _canSubmit: Boolean(root._state.resourceId) && Boolean(root._state.periodStart)
    readonly property bool _canUnlock: Boolean(root._state.periodId)
    readonly property string _assignmentStatus: String(root.assignmentSummary.statusLabel || "")
    readonly property string _assignmentTitle: String(root.assignmentSummary.title || "Task Assignment")
    readonly property string _assignmentSubtitle: String(root.assignmentSummary.subtitle || "")
    readonly property string _resourceValue: root._fieldValue("Resource", "Not assigned")
    readonly property string _hoursValue: root._fieldValue("Hours", "0.00")
    readonly property string _hoursSupportingText: root._fieldSupportingText("Hours", "")
    readonly property string _submittedByValue: root._fieldValue("Submitted by", "Not submitted")
    readonly property string _submittedBySupportingText: root._fieldSupportingText("Submitted by", "")
    readonly property string _decisionValue: root._fieldValue("Decision", "Pending review")
    readonly property string _decisionSupportingText: root._fieldSupportingText("Decision", "")

    function _fieldValue(label, fallbackValue) {
        const wanted = String(label || "")
        const fields = root._summaryFields
        for (let i = 0; i < fields.length; i += 1) {
            const field = fields[i] || {}
            if (String(field.label || "") === wanted)
                return String(field.value || fallbackValue || "")
        }
        return String(fallbackValue || "")
    }

    function _fieldSupportingText(label, fallbackValue) {
        const wanted = String(label || "")
        const fields = root._summaryFields
        for (let i = 0; i < fields.length; i += 1) {
            const field = fields[i] || {}
            if (String(field.label || "") === wanted)
                return String(field.supportingText || fallbackValue || "")
        }
        return String(fallbackValue || "")
    }
    Layout.fillWidth: true
    implicitHeight: _workflowGrid.implicitHeight

    GridLayout {
        id: _workflowGrid
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        columns: width >= 980 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _workflowSummaryColumn.implicitHeight + Theme.AppTheme.marginMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            ColumnLayout {
                id: _workflowSummaryColumn
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: "Approval Context"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: "Review the current period posture before submitting, locking, or reopening labor."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: root._assignmentStatus.length > 0
                        status: root._assignmentStatus
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: _workflowAssignmentColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    ColumnLayout {
                        id: _workflowAssignmentColumn
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: 3

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._assignmentTitle
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._assignmentSubtitle.length > 0 ? root._assignmentSubtitle : root._resourceValue
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.selectedPeriodStart.length > 0
                                ? "Selected period: " + root.selectedPeriodStart
                                : "A timesheet period is required for approval workflow."
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 720 ? 2 : 1
                    columnSpacing: Theme.AppTheme.spacingSm
                    rowSpacing: Theme.AppTheme.spacingSm

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _resourceSummaryColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _resourceSummaryColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Resource"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root._resourceValue
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _hoursSummaryColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _hoursSummaryColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Hours"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root._hoursValue
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: root._hoursSupportingText.length > 0
                                text: root._hoursSupportingText
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _submittedSummaryColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _submittedSummaryColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Submitted by"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root._submittedByValue
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: root._submittedBySupportingText.length > 0
                                text: root._submittedBySupportingText
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _decisionSummaryColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _decisionSummaryColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Decision"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root._decisionValue
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: root._decisionSupportingText.length > 0
                                text: root._decisionSupportingText
                                color: Theme.AppTheme.textMuted
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
            Layout.fillWidth: true
            implicitHeight: _workflowActionsColumn.implicitHeight + Theme.AppTheme.marginMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            ColumnLayout {
                id: _workflowActionsColumn
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Period Actions"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Record an optional workflow note, then submit for review, lock approved time, or reopen a period that needs correction."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                AppControls.TextArea {
                    id: _periodNoteArea
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    enabled: !root.isBusy
                    placeholderText: "Optional note for submission, approval lock, or reopening the selected period."
                    wrapMode: TextEdit.WordWrap
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Item { Layout.fillWidth: true }

                    AppControls.PrimaryButton {
                        text: "Submit Period"
                        iconName: "approve"
                        enabled: !root.isBusy && root._canSubmit
                        onClicked: root.submitRequested({
                            "resourceId": root._state.resourceId || "",
                            "periodStart": root._state.periodStart || "",
                            "note": _periodNoteArea.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text: "Lock"
                        iconName: "approve"
                        enabled: !root.isBusy && root._canSubmit
                        onClicked: root.lockRequested({
                            "resourceId": root._state.resourceId || "",
                            "periodStart": root._state.periodStart || "",
                            "note": _periodNoteArea.text
                        })
                    }

                    AppControls.SecondaryButton {
                        text: "Unlock"
                        iconName: "close"
                        enabled: !root.isBusy && root._canUnlock
                        onClicked: root.unlockRequested({
                            "periodId": root._state.periodId || "",
                            "note": _periodNoteArea.text
                        })
                    }
                }
            }
        }
    }
}

