pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var resourceDetail: ({ "id": "", "title": "" })
    property var resourceAvailabilityModel: ({
        "resourceId": "", "peakLoadPercent": 0, "averageLoadPercent": 0,
        "overloadedDays": 0, "availableDays": 0, "isAvailable": true,
        "fromDateLabel": "", "toDateLabel": "", "days": []
    })
    property bool isBusy: false

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0
    readonly property string _windowLabel: {
        const fromLabel = String(root.resourceAvailabilityModel.fromDateLabel || "")
        const toLabel = String(root.resourceAvailabilityModel.toDateLabel || "")
        if (fromLabel.length > 0 && toLabel.length > 0)
            return fromLabel + " - " + toLabel
        if (fromLabel.length > 0)
            return fromLabel
        return "Availability window not loaded"
    }
    readonly property var _calendarRows: {
        const days = root.resourceAvailabilityModel.days || []
        const rows = []
        const count = Math.min(days.length, 10)
        for (let index = 0; index < count; index += 1) {
            const day = days[index] || {}
            rows.push({
                "id": String(index),
                "date": String(day.dateLabel || ""),
                "allocation": String(day.allocationLabel || ""),
                "status": day.overloaded ? "Overloaded" : "Available",
                "details": day.overloaded
                    ? "Shared calendar working day with overload pressure."
                    : "Shared calendar working day within available capacity."
            })
        }
        return rows
    }
    readonly property real _tableHeight: Theme.AppTheme.headerHeight
        + (Math.max(1, Math.min(_calendarRows.length, 10)) * Theme.AppTheme.normalRowHeight)
        + Theme.AppTheme.spacingLg

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading {
            width: parent.width
            label: "Calendar"
        }

        AppWidgets.ContextualActionToolbar {
            width: parent.width
            title: root._hasResource ? root.resourceDetail.title : "Calendar"
            subtitle: root._hasResource ? "Shared calendar context and availability footprint" : ""
            busy: root.isBusy
            actions: []
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root._hasResource
            title: "No resource selected"
            message: "Select a resource to review its shared calendar context and capacity window."
        }

        ColumnLayout {
            visible: root._hasResource
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                tone: "info"
                message: "Shared working calendars are managed in Platform Admin. PM Resources consumes that calendar for availability and allocation context, but does not manage local calendar CRUD."
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                implicitHeight: summaryGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                title: "Shared Calendar Context"
                outlined: true

                GridLayout {
                    id: summaryGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    columns: 2
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: [
                            { "label": "Calendar Source", "value": "Platform shared working calendar" },
                            { "label": "Availability Window", "value": root._windowLabel },
                            { "label": "Peak Load", "value": String(root.resourceAvailabilityModel.peakLoadPercent || 0) + "%" },
                            { "label": "Average Load", "value": String(root.resourceAvailabilityModel.averageLoadPercent || 0) + "%" },
                            { "label": "Available Days", "value": String(root.resourceAvailabilityModel.availableDays || 0) },
                            { "label": "Overloaded Days", "value": String(root.resourceAvailabilityModel.overloadedDays || 0) }
                        ]

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

            AppWidgets.DataTable {
                Layout.fillWidth: true
                Layout.preferredHeight: root._tableHeight
                rows: root._calendarRows
                columns: [
                    { "key": "date", "label": "Date", "flex": 1.0, "sortable": true },
                    { "key": "allocation", "label": "Allocation", "flex": 1.0 },
                    { "key": "status", "label": "Status", "flex": 0.9, "type": "status" },
                    { "key": "details", "label": "Calendar Impact", "flex": 2.0 }
                ]
                loading: root.isBusy
                emptyText: "No calendar-backed availability rows are available for this resource."
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                tone: "info"
                message: "Resource-specific leave, shift exceptions, and local overrides are not yet modeled in PM Resources. Use the shared Platform calendar as the source of truth for common working days."
            }
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }
    }
}
