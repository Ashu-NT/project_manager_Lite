pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var assignmentSummary: AppMock.MockFactory.fieldRecord("", "", "Select a task assignment.")
    property var assignmentOptions: []
    property var periodOptions: []
    property string selectedPeriodStart: ""
    property var entriesModel: AppMock.MockFactory.catalog("Time Entries", "", "Select a task assignment.")
    property var entriesTableModel: null
    property var selectedEntryDetail: AppMock.MockFactory.fieldRecord()
    property string selectedEntryId: ""
    property bool isBusy: false
    property string errorText: ""

    signal periodChanged(string periodStart)
    signal assignmentChanged(string assignmentId)
    signal entrySelected(string entryId)
    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)
    signal submitRequested(var payload)
    signal lockRequested(var payload)
    signal unlockRequested(var payload)

    readonly property var _items: root.entriesModel.items || []
    readonly property var _state: root.assignmentSummary.state || {}
    readonly property var _entryState: root.selectedEntryDetail.state || {}
    readonly property var _summaryFields: root.assignmentSummary.fields || []
    readonly property bool _hasAssignment: Boolean(root._state.assignmentId)
    readonly property bool _hasEntry: Boolean(root._entryState.entryId)
    readonly property bool _canSubmit: Boolean(root._state.resourceId) && Boolean(root._state.periodStart)
    readonly property bool _canUnlock: Boolean(root._state.periodId)
    readonly property string _assignmentStatus: String(root.assignmentSummary.statusLabel || "")
    readonly property string _assignmentTitle: String(root.assignmentSummary.title || "Task Assignment")
    readonly property string _assignmentSubtitle: String(root.assignmentSummary.subtitle || "")
    readonly property string _assignmentDescription: String(root.assignmentSummary.description || "")
    readonly property string _selectedEntryTitle: String(root.selectedEntryDetail.title || "")
    readonly property string _selectedEntrySubtitle: String(root.selectedEntryDetail.subtitle || "")
    readonly property string _selectedEntryStatus: String(root.selectedEntryDetail.statusLabel || "")

    readonly property int _tableH: {
        const count = root._items.length
        const natural = Theme.AppTheme.normalRowHeight + Math.max(count, 1) * Theme.AppTheme.compactRowHeight + 24
        return Math.max(240, Math.min(natural, 420))
    }

    readonly property var _columns: [
        { key: "title", label: "Period / Date", flex: 2, sortable: false },
        { key: "subtitle", label: "Resource", flex: 2, sortable: false },
        { key: "metaText", label: "Hours / Note", flex: 2, sortable: false },
        { key: "statusLabel", label: "Status", flex: 0, minWidth: 90, type: "status" }
    ]

    onSelectedEntryDetailChanged: {
        if (root._entryState.entryId) {
            _dateField.text = String(root._entryState.entryDate || "")
            _hoursField.text = String(root._entryState.hours || "")
            _noteArea.text = String(root._entryState.note || "")
        } else {
            _dateField.text = ""
            _hoursField.text = ""
            _noteArea.text = ""
        }
    }

    implicitHeight: Math.min(_contentColumn.implicitHeight, 640)

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: _contentColumn.implicitHeight
        clip: true
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: _contentColumn
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.ContextualActionToolbar {
                Layout.fillWidth: true
                title: "Time"
                subtitle: root._assignmentStatus.length > 0
                    ? root._assignmentStatus
                    : (root._items.length > 0 ? root._items.length + " entries" : "Capture and approve task time")
                busy: root.isBusy
                createLabel: ""
                actions: []
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root.errorText.length > 0
                tone: "danger"
                message: root.errorText
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Assignment & Period"

                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _assignmentCardColumn.implicitHeight + Theme.AppTheme.marginMd * 2

                    ColumnLayout {
                        id: _assignmentCardColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._assignmentTitle
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.sectionSize
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
                                    elide: Text.ElideRight
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
                            }

                            AppWidgets.StatusChip {
                                visible: root._assignmentStatus.length > 0
                                status: root._assignmentStatus
                            }
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

                        GridLayout {
                            Layout.fillWidth: true
                            visible: root._summaryFields.length > 0
                            columns: width >= 920 ? 4 : width >= 620 ? 2 : 1
                            columnSpacing: Theme.AppTheme.spacingSm
                            rowSpacing: Theme.AppTheme.spacingSm

                            Repeater {
                                model: root._summaryFields
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: _fieldColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    radius: Theme.AppTheme.radiusMd
                                    color: Theme.AppTheme.surfaceAlt
                                    border.color: Theme.AppTheme.subtleBorder
                                    border.width: 1

                                    ColumnLayout {
                                        id: _fieldColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
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
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Capture Entry"

                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _captureColumn.implicitHeight + Theme.AppTheme.marginMd * 2

                    ColumnLayout {
                        id: _captureColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        Rectangle {
                            Layout.fillWidth: true
                            visible: root._hasEntry
                            implicitHeight: _selectedEntryColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surfaceAlt
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                ColumnLayout {
                                    id: _selectedEntryColumn
                                    Layout.fillWidth: true
                                    spacing: 3

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: "Editing selected entry"
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold: true
                                    }

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: root._selectedEntryTitle
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        visible: root._selectedEntrySubtitle.length > 0
                                        text: root._selectedEntrySubtitle
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        elide: Text.ElideRight
                                    }
                                }

                                AppWidgets.StatusChip {
                                    visible: root._selectedEntryStatus.length > 0
                                    status: root._selectedEntryStatus
                                }
                            }
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
                                    text: "Date"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.DateField {
                                    id: _dateField
                                    Layout.fillWidth: true
                                    enabled: !root.isBusy && root._hasAssignment
                                    placeholderText: "YYYY-MM-DD"
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                AppControls.Label {
                                    text: "Hours"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.TextField {
                                    id: _hoursField
                                    Layout.fillWidth: true
                                    enabled: !root.isBusy && root._hasAssignment
                                    placeholderText: "8.00"
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            AppControls.Label {
                                text: "Labor Note"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.TextArea {
                                id: _noteArea
                                Layout.fillWidth: true
                                Layout.preferredHeight: 88
                                enabled: !root.isBusy && root._hasAssignment
                                placeholderText: "Describe the work completed, blockers, and key deliverables for this entry."
                                wrapMode: TextEdit.WordWrap
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root._hasEntry
                                    ? "Update or remove the selected entry, or clear the selection to capture a new one."
                                    : "Add a new labor entry for the selected assignment and period."
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }

                            AppControls.PrimaryButton {
                                text: "Add Entry"
                                iconName: "add"
                                enabled: !root.isBusy && root._hasAssignment
                                onClicked: root.addRequested({
                                    "assignmentId": root._state.assignmentId || "",
                                    "entryDate": _dateField.text,
                                    "hours": _hoursField.text,
                                    "note": _noteArea.text
                                })
                            }

                            AppControls.SecondaryButton {
                                text: "Update"
                                iconName: "edit"
                                enabled: !root.isBusy && root._hasEntry
                                onClicked: root.updateRequested({
                                    "entryId": root._entryState.entryId || "",
                                    "entryDate": _dateField.text,
                                    "hours": _hoursField.text,
                                    "note": _noteArea.text
                                })
                            }

                            AppControls.SecondaryButton {
                                text: "Delete"
                                iconName: "delete"
                                danger: true
                                enabled: !root.isBusy && root._hasEntry
                                onClicked: root.deleteRequested(String(root._entryState.entryId || ""))
                            }
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Entry Ledger"

                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _ledgerColumn.implicitHeight + Theme.AppTheme.marginMd * 2

                    ColumnLayout {
                        id: _ledgerColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.entriesModel.subtitle || "Detailed labor entries for the selected task assignment."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root._tableH

                            AppWidgets.DataTable {
                                anchors.fill: parent
                                columns: root._columns
                                sourceModel: root.entriesTableModel
                                selectedRowId: root.selectedEntryId
                                loading: root.isBusy
                                emptyText: root.entriesModel.emptyState || "No time entries for this period."

                                onRowSelected: function(rowId) {
                                    root.entrySelected(rowId)
                                }
                                onRowActivated: function(rowId) {
                                    root.entrySelected(rowId)
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._items.length > 0
                                ? "Select a row to edit captured hours or review the labor note before period approval."
                                : "Entries will appear here once labor is captured for the selected assignment and period."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                visible: root._canSubmit || root._canUnlock
                title: "Period Workflow"

                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _periodColumn.implicitHeight + Theme.AppTheme.marginMd * 2

                    ColumnLayout {
                        id: _periodColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Ready for approval"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Submit the selected period for review, lock approved labor, or reopen a locked period when corrections are required."
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

                        AppControls.TextArea {
                            id: _periodNoteArea
                            Layout.fillWidth: true
                            Layout.preferredHeight: 72
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
    }
}
