pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property string resourceId: ""
    property bool isBusy: false
    property bool _initialized: false
    property int _presetDays: 30
    property string _rangeError: ""
    property int _activeTabIndex: 0

    readonly property var _availability: root.workspaceController
        ? (root.workspaceController.resourceAvailability || {}) : ({})
    readonly property var _days: root._availability.days || []
    readonly property var _tabs: [
        { "id": "summary", "label": "Summary" },
        { "id": "daily", "label": "Daily Availability" }
    ]
    readonly property bool _hasData: root.resourceId.length > 0
        && String(root._availability.resourceId || "") === root.resourceId
        && String(root._availability.startDate || "").length > 0
    readonly property int _summaryColumns: root.width >= 1040 ? 4
        : (root.width >= 560 ? 2 : 1)
    readonly property int _contextColumns: root.width >= 760 ? 4
        : (root.width >= 460 ? 2 : 1)
    readonly property int _cardChromeHeight: Theme.AppTheme.normalRowHeight
        + Theme.AppTheme.marginMd * 2
    readonly property int _tableHeight: root._days.length === 0
        ? Theme.AppTheme.normalRowHeight + 96
        : Math.min(
            Theme.AppTheme.normalRowHeight
                + root._days.length * Theme.AppTheme.compactRowHeight + 14,
            420
        )
    readonly property var _summaryMetrics: [
        {
            "label": "Effective capacity",
            "value": root._hours(root._availability.effectiveCapacityHours),
            "supporting": "Calendar capacity after the Resource modifier."
        },
        {
            "label": "Planned commitment",
            "value": root._hours(root._availability.plannedCommitmentHours),
            "supporting": "Task assignment demand in this window."
        },
        {
            "label": "Remaining capacity",
            "value": root._hours(root._availability.remainingCapacityHours),
            "supporting": root._availability.overallocated === true
                ? "Negative capacity identifies unresolved overload."
                : "Capacity still available in this window."
        },
        {
            "label": "Planned utilization",
            "value": String(root._availability.utilizationLabel || "N/A"),
            "supporting": "Commitment divided by effective capacity."
        }
    ]
    readonly property var _dailyColumns: [
        { key: "dateLabel", label: "Date", flex: 1, minWidth: 90, sortable: false },
        { key: "baseCapacityLabel", label: "Calendar", flex: 1, minWidth: 88, sortable: false },
        { key: "effectiveCapacityLabel", label: "Effective", flex: 1, minWidth: 88, sortable: false },
        { key: "plannedCommitmentLabel", label: "Committed", flex: 1, minWidth: 92, sortable: false },
        { key: "remainingCapacityLabel", label: "Remaining", flex: 1, minWidth: 92, sortable: false },
        { key: "utilizationLabel", label: "Utilization", flex: 1, minWidth: 92, sortable: false },
        { key: "assignmentCount", label: "Assignments", flex: 0, minWidth: 94, sortable: false },
        { key: "statusLabel", label: "Status", flex: 0, minWidth: 112, type: "status", sortable: false }
    ]

    function _hours(value) {
        const number = Number(value || 0)
        return number.toLocaleString(Qt.locale(), "f", 1) + " h"
    }

    function _isoDateWithOffset(offsetDays) {
        const value = new Date()
        value.setDate(value.getDate() + offsetDays)
        return Qt.formatDate(value, "yyyy-MM-dd")
    }

    function _isIsoDate(value) {
        return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))
    }

    function _syncRangeFromResult() {
        if (!root._hasData) return
        fromDate.text = String(root._availability.startDate || "")
        toDate.text = String(root._availability.endDate || "")
    }

    function _requestAvailability(force) {
        if (!root._initialized || root.workspaceController === null
                || root.resourceId.length === 0) return
        const start = String(fromDate.text || "").trim()
        const end = String(toDate.text || "").trim()
        if (!root._isIsoDate(start) || !root._isIsoDate(end)) {
            root._rangeError = "Enter valid start and end dates in YYYY-MM-DD format."
            return
        }
        if (end < start) {
            root._rangeError = "End date must be on or after start date."
            return
        }
        root._rangeError = ""
        root.workspaceController.loadResourceAvailability(start, end)
    }

    function _applyPreset(days) {
        root._presetDays = days
        fromDate.text = root._isoDateWithOffset(0)
        toDate.text = root._isoDateWithOffset(days - 1)
        root._requestAvailability(true)
    }

    function _loadDefault() {
        root._presetDays = 30
        fromDate.text = root._isoDateWithOffset(0)
        toDate.text = root._isoDateWithOffset(29)
        root._requestAvailability(true)
    }

    onResourceIdChanged: {
        root._activeTabIndex = 0
        if (root._initialized) root._loadDefault()
    }

    Component.onCompleted: {
        root._initialized = true
        if (root._hasData) root._syncRangeFromResult()
        else root._loadDefault()
    }

    Connections {
        target: root.workspaceController
        ignoreUnknownSignals: true
        function onResourceAvailabilityChanged() {
            root._syncRangeFromResult()
        }
    }

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: "Availability window"
            outlined: true
            implicitHeight: rangeContent.implicitHeight + root._cardChromeHeight

            ColumnLayout {
                id: rangeContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Capacity is resolved from enterprise calendars and compared with Task Assignment commitments across projects."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Flow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: childrenRect.height
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.SecondaryButton {
                        text: "30 days"
                        enabled: !root.isBusy
                        onClicked: root._applyPreset(30)
                    }
                    AppControls.SecondaryButton {
                        text: "60 days"
                        enabled: !root.isBusy
                        onClicked: root._applyPreset(60)
                    }
                    AppControls.SecondaryButton {
                        text: "90 days"
                        enabled: !root.isBusy
                        onClicked: root._applyPreset(90)
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width >= 680 ? 3 : 1
                    columnSpacing: Theme.AppTheme.spacingSm
                    rowSpacing: Theme.AppTheme.spacingSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label {
                            text: "FROM"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.DateField {
                            id: fromDate
                            Layout.fillWidth: true
                            popupBoundaryItem: root
                            enabled: !root.isBusy
                            onDateSelected: root._presetDays = 0
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label {
                            text: "TO"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.DateField {
                            id: toDate
                            Layout.fillWidth: true
                            popupBoundaryItem: root
                            enabled: !root.isBusy
                            onDateSelected: root._presetDays = 0
                        }
                    }

                    AppControls.PrimaryButton {
                        Layout.alignment: Qt.AlignBottom
                        text: root.isBusy ? "Loading" : "Apply range"
                        iconName: "refresh"
                        enabled: !root.isBusy && root.resourceId.length > 0
                        onClicked: {
                            root._presetDays = 0
                            root._requestAvailability(true)
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._rangeError.length > 0
                    tone: "danger"
                    message: root._rangeError
                }
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.resourceId.length === 0
            title: "No resource selected"
            message: "Select a resource to review its calendar-backed availability."
        }

        AppWidgets.DetailTabBar {
            Layout.fillWidth: true
            visible: root.resourceId.length > 0
            tabs: root._tabs
            currentIndex: root._activeTabIndex
            onTabSelected: function(index) { root._activeTabIndex = index }
        }

        Item {
            id: tabContentHost
            Layout.fillWidth: true
            visible: root.resourceId.length > 0
            Layout.preferredHeight: root._activeTabIndex === 0
                ? summaryContent.implicitHeight : dailyContent.implicitHeight
            implicitHeight: Layout.preferredHeight

            ColumnLayout {
                id: summaryContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: Theme.AppTheme.spacingSm
                visible: root._activeTabIndex === 0

                GridLayout {
                    Layout.fillWidth: true
                    columns: root._summaryColumns
                    columnSpacing: Theme.AppTheme.spacingSm
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._summaryMetrics
                        delegate: AppWidgets.MetricCard {
                            id: metricCard
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 124
                            label: String(metricCard.modelData.label || "")
                            value: root._hasData ? String(metricCard.modelData.value || "") : "--"
                            supportingText: String(metricCard.modelData.supporting || "")
                        }
                    }
                }

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Capacity context"
                    outlined: true
                    implicitHeight: contextContent.implicitHeight
                        + root._cardChromeHeight + Theme.AppTheme.spacingLg

                    ColumnLayout {
                        id: contextContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingSm

                            AppWidgets.StatusChip {
                                status: !root._hasData ? "Not loaded"
                                    : (root._availability.overallocated === true
                                        ? "Over capacity" : "Within capacity")
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root._hasData
                                    ? String(root._availability.fromDateLabel || "")
                                        + " to " + String(root._availability.toDateLabel || "")
                                    : "Load a date range to calculate availability."
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide: Text.ElideRight
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: root._contextColumns
                            columnSpacing: Theme.AppTheme.spacingLg
                            rowSpacing: Theme.AppTheme.spacingSm

                            Repeater {
                                model: [
                                    { "label": "Calendar capacity", "value": root._hours(root._availability.baseCapacityHours) },
                                    { "label": "Capacity modifier", "value": Number(root._availability.capacityPercent || 0).toLocaleString(Qt.locale(), "f", 1) + "%" },
                                    { "label": "Projects", "value": String(root._availability.projectCount || 0) },
                                    { "label": "Assignments", "value": String(root._availability.assignmentCount || 0) },
                                    { "label": "Conflict days", "value": String(root._availability.conflictDays || 0) },
                                    { "label": "Allocated planned work", "value": root._hours(root._availability.allocatedPlannedHours) }
                                ]

                                delegate: ColumnLayout {
                                    id: contextFact
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: 2
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(contextFact.modelData.label || "")
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: root._hasData ? String(contextFact.modelData.value || "") : "--"
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._hasData && String(root._availability.calendarSourceLabel || "").length > 0
                                ? "Calendar source: " + String(root._availability.calendarSourceLabel)
                                : "Calendar source will be shown after the range is resolved."
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            ColumnLayout {
                id: dailyContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                visible: root._activeTabIndex === 1
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Daily capacity by date"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.sectionTitleSize
                        font.bold: true
                    }

                    AppControls.Label {
                        visible: root._hasData
                        text: String(root._availability.fromDateLabel || "")
                            + " - " + String(root._availability.toDateLabel || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Read-only calendar facts preserve non-working days and negative remaining capacity."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.rightMargin: Theme.AppTheme.spacingLg
                    Layout.preferredHeight: root._tableHeight
                    radius: Theme.AppTheme.radiusSm
                    color: Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1
                    clip: true

                    AppWidgets.DataTable {
                        anchors.fill: parent
                        anchors.margins: 1
                        columns: root._dailyColumns
                        rows: root._days
                        sortingMode: "none"
                        alwaysShowVerticalScrollBar: root._days.length
                            * Theme.AppTheme.compactRowHeight > root._tableHeight
                        loading: root.isBusy
                        emptyText: root._hasData
                            ? "No calendar days were returned for this range."
                            : "Availability has not been loaded."
                    }
                }
            }
        }
    }
}
