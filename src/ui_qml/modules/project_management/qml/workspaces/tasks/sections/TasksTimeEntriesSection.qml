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

    property int _activeTabIndex: 0

    readonly property var _items: root.entriesModel.items || []
    readonly property var _state: root.assignmentSummary.state || {}
    readonly property var _entryState: root.selectedEntryDetail.state || {}
    readonly property var _entryFields: root.selectedEntryDetail.fields || []
    readonly property var _summaryFields: root.assignmentSummary.fields || []
    readonly property bool _hasAssignment: Boolean(root._state.assignmentId)
    readonly property bool _hasEntry: Boolean(root._entryState.entryId)
    readonly property bool _canSubmit: Boolean(root._state.resourceId) && Boolean(root._state.periodStart)
    readonly property bool _canUnlock: Boolean(root._state.periodId)
    readonly property bool _showWorkflowTab: root._canSubmit || root._canUnlock
    readonly property string _assignmentStatus: String(root.assignmentSummary.statusLabel || "")
    readonly property string _assignmentTitle: String(root.assignmentSummary.title || "Task Assignment")
    readonly property string _assignmentSubtitle: String(root.assignmentSummary.subtitle || "")
    readonly property string _assignmentDescription: String(root.assignmentSummary.description || "")
    readonly property string _selectedEntryTitle: String(root.selectedEntryDetail.title || "")
    readonly property string _selectedEntrySubtitle: String(root.selectedEntryDetail.subtitle || "")
    readonly property string _selectedEntryStatus: String(root.selectedEntryDetail.statusLabel || "")
    readonly property string _resourceValue: root._fieldValue("Resource", "Not assigned")
    readonly property string _hoursValue: root._fieldValue("Hours", "0.00")
    readonly property string _hoursSupportingText: root._fieldSupportingText("Hours", "")
    readonly property string _submittedByValue: root._fieldValue("Submitted by", "Not submitted")
    readonly property string _submittedBySupportingText: root._fieldSupportingText("Submitted by", "")
    readonly property string _decisionValue: root._fieldValue("Decision", "Pending review")
    readonly property string _decisionSupportingText: root._fieldSupportingText("Decision", "")
    readonly property var _detailTabs: {
        const tabs = [
            { "id": "assignment", "label": "Assignment" },
            { "id": "capture", "label": "Capture" },
            { "id": "ledger", "label": "Ledger" }
        ]
        if (root._showWorkflowTab)
            tabs.push({ "id": "workflow", "label": "Workflow" })
        return tabs
    }
    readonly property int _resolvedTabIndex: {
        const tabs = root._detailTabs
        if (!tabs.length)
            return 0
        return Math.max(0, Math.min(root._activeTabIndex, tabs.length - 1))
    }
    readonly property real _activePanelHeight: {
        if (root._resolvedTabIndex === 1)
            return _capturePanel.implicitHeight
        if (root._resolvedTabIndex === 2)
            return _ledgerPanel.implicitHeight
        if (root._resolvedTabIndex === 3)
            return _workflowPanel.implicitHeight
        return _assignmentPanel.implicitHeight
    }

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

    function _syncEditorFields() {
        if (!_dateField || !_hoursField || !_noteArea)
            return
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

    onSelectedEntryDetailChanged: Qt.callLater(root._syncEditorFields)
    Component.onCompleted: root._syncEditorFields()

    implicitHeight: _contentColumn.implicitHeight
    height: implicitHeight

    ColumnLayout {
        id: _contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
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

        AppWidgets.DetailTabBar {
            Layout.fillWidth: true
            tabs: root._detailTabs
            currentIndex: root._resolvedTabIndex
            onTabSelected: function(index) {
                root._activeTabIndex = index
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: root._activePanelHeight
            implicitHeight: root._activePanelHeight
            currentIndex: root._resolvedTabIndex

            Item {
                id: _assignmentPanel
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

            Item {
                id: _capturePanel
                Layout.fillWidth: true
                implicitHeight: _captureGrid.implicitHeight

                GridLayout {
                    id: _captureGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    columns: width >= 980 ? 2 : 1
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingMd

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _captureEditorColumn.implicitHeight + Theme.AppTheme.marginMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceRaised
                        border.color: Theme.AppTheme.subtleBorder
                        border.width: 1

                        ColumnLayout {
                            id: _captureEditorColumn
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
                                        text: "Capture Labor Entry"
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.bodySize
                                        font.bold: true
                                    }

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: "Log daily hours and update the selected time entry without leaving the task workspace."
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                Rectangle {
                                    implicitWidth: _entryModeLabel.implicitWidth + Theme.AppTheme.spacingMd * 2
                                    implicitHeight: Theme.AppTheme.toolbarHeight
                                    radius: Theme.AppTheme.radiusSm
                                    color: root._hasEntry ? Theme.AppTheme.accentSoft : Theme.AppTheme.surfaceAlt
                                    border.color: Theme.AppTheme.subtleBorder
                                    border.width: 1

                                    AppControls.Label {
                                        id: _entryModeLabel
                                        anchors.centerIn: parent
                                        text: root._hasEntry ? "Selected entry" : "New entry"
                                        color: root._hasEntry ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                    }
                                }
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
                                    Layout.preferredHeight: 120
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
                                    text: root._hasAssignment
                                        ? "Capture work against the selected assignment and period."
                                        : "Choose a task assignment before logging labor."
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

                    Rectangle {
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
                }
            }

            Item {
                id: _ledgerPanel
                Layout.fillWidth: true
                implicitHeight: _ledgerFrame.implicitHeight

                Rectangle {
                    id: _ledgerFrame
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    implicitHeight: _ledgerColumn.implicitHeight + Theme.AppTheme.marginMd * 2
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    ColumnLayout {
                        id: _ledgerColumn
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
                                    text: "Entry Ledger"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root.entriesModel.subtitle || "Detailed labor entries for the selected task assignment."
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WordWrap
                                }
                            }

                            Rectangle {
                                implicitWidth: _ledgerCountLabel.implicitWidth + Theme.AppTheme.spacingMd * 2
                                implicitHeight: Theme.AppTheme.toolbarHeight
                                radius: Theme.AppTheme.radiusSm
                                color: Theme.AppTheme.surfaceAlt
                                border.color: Theme.AppTheme.subtleBorder
                                border.width: 1

                                AppControls.Label {
                                    id: _ledgerCountLabel
                                    anchors.centerIn: parent
                                    text: root._items.length > 0 ? root._items.length + " entries" : "No entries"
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.AppTheme.divider
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
                                ? "Select a row to move directly into capture mode for corrections, notes, or hour adjustments."
                                : "Entries will appear here once labor is captured for the selected assignment and period."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Item {
                id: _workflowPanel
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
        }
    }
}
