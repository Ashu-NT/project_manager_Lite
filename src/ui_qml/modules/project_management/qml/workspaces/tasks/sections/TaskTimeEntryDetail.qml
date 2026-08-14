pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var assignmentSummary: ({})
    property var selectedEntryDetail: ({})
    property string selectedPeriodStart: ""

    readonly property var _summaryFields: root.assignmentSummary.fields || []
    readonly property var _entryState: root.selectedEntryDetail.state || {}
    readonly property var _entryFields: root.selectedEntryDetail.fields || []
    readonly property bool _hasEntry: Boolean(root._entryState.entryId)
    readonly property string _assignmentTitle: String(root.assignmentSummary.title || "Task Assignment")
    readonly property string _assignmentSubtitle: String(root.assignmentSummary.subtitle || "")
    readonly property string _selectedEntryTitle: String(root.selectedEntryDetail.title || "")
    readonly property string _selectedEntrySubtitle: String(root.selectedEntryDetail.subtitle || "")
    readonly property string _selectedEntryStatus: String(root.selectedEntryDetail.statusLabel || "")
    readonly property string _resourceValue: root._fieldValue("Resource", "Not assigned")

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

    Layout.fillWidth: true
    implicitHeight: _captureContextColumn.implicitHeight + Theme.AppTheme.marginMd * 2
    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surfaceRaised
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1

    ColumnLayout {
        id: _captureContextColumn
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                Layout.fillWidth: true
                text: "Entry Context"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppWidgets.StatusChip {
                visible: root._selectedEntryStatus.length > 0
                status: root._selectedEntryStatus
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _contextSummaryColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceAlt
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            ColumnLayout {
                id: _contextSummaryColumn
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: 3

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root._hasEntry ? root._selectedEntryTitle : "No entry selected"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                    elide: Text.ElideRight
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: root._hasEntry && root._selectedEntrySubtitle.length > 0
                    text: root._selectedEntrySubtitle
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    elide: Text.ElideRight
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root._hasEntry
                        ? "Updating the current row keeps the ledger and approval context aligned to this task."
                        : "Select a ledger row to edit an existing entry, or stay in new-entry mode to add fresh labor."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 1
            rowSpacing: Theme.AppTheme.spacingSm

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: _assignmentContextColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1

                ColumnLayout {
                    id: _assignmentContextColumn
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: 3

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Assignment Context"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

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
                            ? "Period: " + root.selectedPeriodStart
                            : "Choose a period to align entry capture."
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: root._entryFields.length > 0
                implicitHeight: _entryDetailsColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1

                ColumnLayout {
                    id: _entryDetailsColumn
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Selected Entry Details"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    Repeater {
                        model: root._entryFields

                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.value || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}

