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
    property var assignmentOptions: []
    property var periodOptions: []
    property string selectedPeriodStart: ""
    property bool isBusy: false

    signal assignmentChanged(string assignmentId)
    signal periodChanged(string periodStart)

    readonly property var _state: root.assignmentSummary.state || {}
    readonly property var _summaryFields: root.assignmentSummary.fields || []
    readonly property bool _hasAssignment: Boolean(root._state.assignmentId)
    readonly property string _assignmentStatus: String(root.assignmentSummary.statusLabel || "")
    readonly property string _assignmentTitle: String(root.assignmentSummary.title || "Task Assignment")
    readonly property string _assignmentSubtitle: String(root.assignmentSummary.subtitle || "")
    readonly property string _assignmentDescription: String(root.assignmentSummary.description || "")
    Layout.fillWidth: true
    implicitHeight: _assignmentLayout.implicitHeight

    ColumnLayout {
        id: _assignmentLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _assignmentHeaderColumn.implicitHeight + Theme.AppTheme.marginMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            ColumnLayout {
                id: _assignmentHeaderColumn
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
                            text: root._assignmentTitle
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: root._assignmentSubtitle.length > 0
                            text: root._assignmentSubtitle
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

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: root._assignmentDescription.length > 0
                    text: root._assignmentDescription
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.AppTheme.divider
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 760 ? 2 : 1
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        AppControls.Label {
                            text: "Task Assignment"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.ComboBox {
                            Layout.fillWidth: true
                            model: root.assignmentOptions
                            textRole: "label"
                            enabled: !root.isBusy
                            currentIndex: {
                                const options = root.assignmentOptions
                                const assignmentId = String(root._state.assignmentId || "")
                                for (let i = 0; i < options.length; i += 1) {
                                    if (String(options[i].value || "") === assignmentId)
                                        return i
                                }
                                return 0
                            }
                            onActivated: function(index) {
                                const option = root.assignmentOptions[index]
                                if (option)
                                    root.assignmentChanged(String(option.value || ""))
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        AppControls.Label {
                            text: "Period"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.ComboBox {
                            Layout.fillWidth: true
                            model: root.periodOptions
                            textRole: "label"
                            enabled: !root.isBusy
                            currentIndex: {
                                const options = root.periodOptions
                                const value = String(root.selectedPeriodStart || "")
                                for (let i = 0; i < options.length; i += 1) {
                                    if (String(options[i].value || "") === value)
                                        return i
                                }
                                return 0
                            }
                            onActivated: function(index) {
                                const option = root.periodOptions[index]
                                if (option)
                                    root.periodChanged(String(option.value || ""))
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            visible: root._summaryFields.length > 0
            implicitHeight: _summaryGrid.implicitHeight + Theme.AppTheme.marginMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            GridLayout {
                id: _summaryGrid
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                columns: width >= 920 ? 4 : width >= 620 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingSm
                rowSpacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: root._summaryFields

                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: _fieldTileColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _fieldTileColumn
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: 3

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                                elide: Text.ElideRight
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

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: String(modelData.supportingText || "").length > 0
                                text: String(modelData.supportingText || "")
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

        AppControls.Label {
            Layout.fillWidth: true
            visible: !root._hasAssignment && String(root.assignmentSummary.emptyState || "").length > 0
            text: root.assignmentSummary.emptyState || ""
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}


