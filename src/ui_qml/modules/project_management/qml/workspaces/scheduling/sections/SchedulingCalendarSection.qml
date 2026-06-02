pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var calendarModel: ({
        "summaryText": "",
        "workingDays": [],
        "hoursPerDay": "8",
        "holidays": [],
        "emptyState": ""
    })
    property string calculatorResult: ""
    property bool isBusy: false

    signal calculateRequested(var payload)

    readonly property var workingDayStates: {
        return (root.calendarModel.workingDays || []).filter(function(day) {
            return Boolean(day.checked)
        })
    }

    implicitHeight: calendarLayout.implicitHeight

    GridLayout {
        id: calendarLayout

        width: parent ? parent.width : implicitWidth
        columns: width > 1120 ? 3 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            implicitHeight: settingsColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: settingsColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Working Calendar"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: String(root.calendarModel.summaryText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root.workingDayStates

                        delegate: Rectangle {
                            required property var modelData
                            height: 28
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.navSelectedBackground
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1
                            width: dayLabel.implicitWidth + Theme.AppTheme.spacingLg

                            AppControls.Label {
                                id: dayLabel
                                anchors.centerIn: parent
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.accent
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }
                        }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Hours / day: " + String(root.calendarModel.hoursPerDay || "8")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Shared working calendars are managed in Platform Admin. Scheduling consumes them read-only here."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            implicitHeight: calculatorColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: calculatorColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Working-Day Calculator"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Preview finish dates using the current working calendar and non-working days."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                AppControls.DateField {
                    id: calculatorStartDateField
                    Layout.fillWidth: true
                    placeholderText: "Start date (YYYY-MM-DD)"
                    enabled: !root.isBusy
                }

                AppControls.TextField {
                    id: calculatorDaysField
                    Layout.fillWidth: true
                    placeholderText: "Working days"
                    enabled: !root.isBusy
                }

                AppControls.PrimaryButton {
                    text: "Calculate"
                    iconName: "filter"
                    enabled: !root.isBusy
                    onClicked: root.calculateRequested({
                        "startDate": calculatorStartDateField.text,
                        "workingDays": calculatorDaysField.text
                    })
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: String(root.calculatorResult || "Run the calculator to preview the working-day finish date.")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            implicitHeight: holidaysColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: holidaysColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Non-Working Days"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Shared non-working-day exceptions are maintained in Platform Admin and shown here for schedule visibility."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                ProjectManagementWidgets.RecordListCard {
                    Layout.fillWidth: true
                    title: "Holiday Register"
                    subtitle: "These days are skipped during scheduling and working-day calculations."
                    emptyState: String(root.calendarModel.emptyState || "")
                    items: root.calendarModel.holidays || []
                    actionsEnabled: false
                }
            }
        }
    }
}
