pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Full detail for one selected Month-grid date -- every field comes from
// the same backend-resolved CalendarDayViewModel the grid cell itself uses,
// never a second calculation. No date is selected -> emptyLabel.
Item {
    id: root

    property var dayData: null
    property bool canWrite: true

    signal addExceptionRequested(string date)

    implicitHeight: content.implicitHeight

    readonly property bool _hasSelection: root.dayData !== null
    readonly property var _fields: {
        if (!root._hasSelection) return []
        const d = root.dayData
        const rows = []
        rows.push({ "label": "Status", "value": d.isWorkingDay ? "Working day" : "Non-working day" })
        if (d.isWorkingDay) {
            rows.push({ "label": "Available Hours", "value": (Number(d.availableHours) % 1 === 0 ? Number(d.availableHours) + " h" : Number(d.availableHours).toFixed(1) + " h") })
        }
        if (d.startTimeLabel && d.endTimeLabel) {
            rows.push({ "label": "Working Time", "value": d.startTimeLabel + "–" + d.endTimeLabel })
        }
        if (d.exceptionTypeLabel) {
            rows.push({ "label": "Exception", "value": d.exceptionTypeLabel })
        }
        if (d.impactLabel) {
            rows.push({ "label": "Impact", "value": d.impactLabel })
        }
        return rows
    }

    AppWidgets.SectionCard {
        id: card
        width: parent ? parent.width : root.width
        implicitHeight: content.implicitHeight + Theme.AppTheme.spacingMd * 2
        title: root._hasSelection ? String(root.dayData.dateLabel || "") : "Select a day"
        outlined: true

        ColumnLayout {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                visible: !root._hasSelection
                text: "Select a date in the month grid to see its working status, hours, and any exceptions."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Repeater {
                model: root._fields

                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 2

                    AppControls.Label {
                        text: String(modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(modelData.value || "-")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }
                }
            }

            AppControls.SecondaryButton {
                Layout.fillWidth: true
                visible: root._hasSelection && root.canWrite
                text: "Add Exception"
                iconName: "add"
                onClicked: root.addExceptionRequested(String(root.dayData.date || ""))
            }
        }
    }
}
