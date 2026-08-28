pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var profile: ({ "id": "", "fields": [] })
    property var schedule: ({ "items": [] })
    property var preparations: ({ "items": [] })
    property var selectedPreparation: ({ "id": "", "fields": [] })
    property var lines: ({ "items": [] })
    property var scheduleTableModel: null
    property var preparationsTableModel: null
    property var linesTableModel: null
    property string selectedPreparationId: ""
    property string scheduleSortKey: "supportingText"
    property int scheduleSortDirection: Qt.AscendingOrder
    property string preparationSortKey: "metaText"
    property int preparationSortDirection: Qt.DescendingOrder
    property string lineSortKey: "metaText"
    property int lineSortDirection: Qt.AscendingOrder
    property string scheduleSearch: ""
    property string scheduleStatus: ""
    property string scheduleSourceState: ""
    property string preparationSearch: ""
    property string preparationStatus: ""
    property string preparationMethod: ""
    property string preparationApprovalStatus: ""
    property string preparationDeliveryState: ""
    property string preparationCorrectionState: ""
    property string lineSearch: ""
    property string lineSourceType: ""
    property string lineSourceState: ""
    property bool busy: false

    signal preparationSelected(string preparationId)
    signal schedulePageRequested(int page)
    signal preparationPageRequested(int page)
    signal linePageRequested(int page)
    signal scheduleSortRequested(string key, int direction)
    signal preparationSortRequested(string key, int direction)
    signal lineSortRequested(string key, int direction)
    signal scheduleFiltersRequested(string search, string status, string sourceState)
    signal preparationFiltersRequested(string search, string status, string method, string approvalStatus, string deliveryState, string correctionState)
    signal lineFiltersRequested(string search, string sourceType, string sourceState)

    readonly property var _scheduleColumns: [
        { "key": "title", "label": "Schedule line", "flex": 1.7, "sortable": true },
        { "key": "statusLabel", "label": "Status", "minWidth": 105, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "Amount", "flex": 1.0, "sortable": true },
        { "key": "supportingText", "label": "Due", "flex": 0.9, "sortable": true },
        { "key": "metaText", "label": "Source / task", "flex": 1.6, "sortable": true }
    ]
    readonly property var _preparationColumns: [
        { "key": "title", "label": "Preparation", "flex": 1.0, "sortable": true },
        { "key": "statusLabel", "label": "Status", "minWidth": 115, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "Method / period", "flex": 1.7, "sortable": true },
        { "key": "supportingText", "label": "Authoritative total", "flex": 1.35, "sortable": true },
        { "key": "metaText", "label": "Delivery truth", "flex": 1.8, "sortable": true }
    ]
    readonly property var _lineColumns: [
        { "key": "title", "label": "Preparation line", "flex": 1.7, "sortable": true },
        { "key": "statusLabel", "label": "Source type", "minWidth": 125, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "Net amount", "flex": 1.0, "sortable": true },
        { "key": "supportingText", "label": "Lock / rate snapshot", "flex": 1.55, "sortable": true },
        { "key": "metaText", "label": "Source evidence", "flex": 1.6, "sortable": true }
    ]
    readonly property var _scheduleStatuses: _options("All statuses", ["planned", "ready", "billed", "cancelled"])
    readonly property var _preparationStatuses: _options("All statuses", ["draft", "submitted", "approved", "delivery_pending", "delivered", "acknowledged", "reconciled", "rejected", "cancelled"])
    readonly property var _methods: _options("All methods", ["time_and_materials", "fixed_price", "cost_plus"])
    readonly property var _approvals: _options("All approvals", ["pending", "approved", "rejected"])
    readonly property var _deliveryStates: _options("Any delivery evidence", ["ready", "local_requested", "external_acknowledged", "not_requested"])
    readonly property var _correctionStates: _options("Original or correction", ["original", "correction"])
    readonly property var _sourceTypes: _options("All source types", ["approved_time", "posted_cost", "schedule_line", "adjustment"])
    readonly property var _sourceStates: _options("Any source state", ["available", "reserved", "finalized", "released"])

    function _label(value) {
        return String(value || "").replaceAll("_", " ").replace(/\b\w/g, function(c) { return c.toUpperCase() })
    }
    function _options(emptyLabel, values) {
        const result = [{ "value": "", "label": emptyLabel }]
        for (let index = 0; index < values.length; index += 1)
            result.push({ "value": values[index], "label": _label(values[index]) })
        return result
    }
    function _indexOf(model, value) {
        for (let index = 0; index < model.length; index += 1)
            if (String(model[index].value) === String(value || "")) return index
        return 0
    }
    function _value(combo, model) {
        const option = model[combo.currentIndex]
        return option ? String(option.value) : ""
    }
    function _emitPreparationFilters(search) {
        root.preparationFiltersRequested(
            search,
            _value(preparationStatusFilter, root._preparationStatuses),
            _value(methodFilter, root._methods),
            _value(approvalFilter, root._approvals),
            _value(deliveryFilter, root._deliveryStates),
            _value(correctionFilter, root._correctionStates)
        )
    }

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: root.profile.title || "Billing Profile"
            ColumnLayout {
                width: parent ? parent.width : 0
                spacing: Theme.AppTheme.spacingSm
                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    text: root.profile.description || "PM-owned commercial setup."
                    color: Theme.AppTheme.textMuted
                    wrapMode: Text.WordWrap
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 900 ? 3 : (width >= 560 ? 2 : 1)
                    Repeater {
                        model: root.profile.fields || []
                        delegate: ColumnLayout {
                            id: profileField
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.margins: Theme.AppTheme.spacingMd
                            AppControls.Label { text: String(profileField.modelData.label || ""); color: Theme.AppTheme.textMuted }
                            AppControls.Label { Layout.fillWidth: true; text: String(profileField.modelData.value || "-"); font.bold: true; wrapMode: Text.WordWrap }
                            AppControls.Label { Layout.fillWidth: true; text: String(profileField.modelData.supportingText || ""); color: Theme.AppTheme.textMuted; wrapMode: Text.WordWrap; visible: text.length > 0 }
                        }
                    }
                }
            }
        }

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Billing Schedule" }
        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.scheduleSearch
            searchPlaceholder: "Search schedule, acceptance, task, or WBS..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) {
                root.scheduleFiltersRequested(text, root._value(scheduleStatusFilter, root._scheduleStatuses), root._value(scheduleSourceFilter, root._sourceStates))
            }
            AppControls.ComboBox {
                id: scheduleStatusFilter
                implicitWidth: 145
                textRole: "label"
                model: root._scheduleStatuses
                currentIndex: root._indexOf(model, root.scheduleStatus)
                onActivated: root.scheduleFiltersRequested(root.scheduleSearch, root._value(scheduleStatusFilter, root._scheduleStatuses), root._value(scheduleSourceFilter, root._sourceStates))
            }
            AppControls.ComboBox {
                id: scheduleSourceFilter
                implicitWidth: 165
                textRole: "label"
                model: root._sourceStates
                currentIndex: root._indexOf(model, root.scheduleSourceState)
                onActivated: root.scheduleFiltersRequested(root.scheduleSearch, root._value(scheduleStatusFilter, root._scheduleStatuses), root._value(scheduleSourceFilter, root._sourceStates))
            }
        }
        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.schedule.items || []).length === 0
            title: "No Billing Schedule"
            message: root.schedule.emptyState || "No schedule lines match the current filters."
        }
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 260
            visible: (root.schedule.items || []).length > 0
            AppWidgets.DataTable {
                anchors.fill: parent
                objectName: "billingScheduleTable"
                columns: root._scheduleColumns
                sourceModel: root.scheduleTableModel
                sortingMode: "server"
                sortKey: root.scheduleSortKey
                sortDirection: root.scheduleSortDirection
                loading: root.busy
                onSortRequested: function(key, direction) { root.scheduleSortRequested(key, direction) }
            }
        }
        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.schedule.total || 0) > Number(root.schedule.pageSize || 50)
            currentPage: Number(root.schedule.page || 1)
            pageSize: Number(root.schedule.pageSize || 50)
            totalItems: Number(root.schedule.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.schedulePageRequested(page) }
        }

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Billing Preparations" }
        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.preparationSearch
            searchPlaceholder: "Search preparation, correction, requester, or external reference..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) { root._emitPreparationFilters(text) }
            AppControls.ComboBox {
                id: preparationStatusFilter
                implicitWidth: 150
                textRole: "label"
                model: root._preparationStatuses
                currentIndex: root._indexOf(model, root.preparationStatus)
                onActivated: root._emitPreparationFilters(root.preparationSearch)
            }
            AppControls.ComboBox {
                id: methodFilter
                implicitWidth: 155
                textRole: "label"
                model: root._methods
                currentIndex: root._indexOf(model, root.preparationMethod)
                onActivated: root._emitPreparationFilters(root.preparationSearch)
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm
            AppControls.ComboBox { id: approvalFilter; width: 155; textRole: "label"; model: root._approvals; currentIndex: root._indexOf(model, root.preparationApprovalStatus); onActivated: root._emitPreparationFilters(root.preparationSearch) }
            AppControls.ComboBox { id: deliveryFilter; width: 210; textRole: "label"; model: root._deliveryStates; currentIndex: root._indexOf(model, root.preparationDeliveryState); onActivated: root._emitPreparationFilters(root.preparationSearch) }
            AppControls.ComboBox { id: correctionFilter; width: 190; textRole: "label"; model: root._correctionStates; currentIndex: root._indexOf(model, root.preparationCorrectionState); onActivated: root._emitPreparationFilters(root.preparationSearch) }
        }
        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.preparations.items || []).length === 0
            title: "No Billing Preparations"
            message: root.preparations.emptyState || "No preparations match the current filters."
        }
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 285
            visible: (root.preparations.items || []).length > 0
            AppWidgets.DataTable {
                anchors.fill: parent
                objectName: "billingPreparationsTable"
                columns: root._preparationColumns
                sourceModel: root.preparationsTableModel
                sortingMode: "server"
                sortKey: root.preparationSortKey
                sortDirection: root.preparationSortDirection
                selectedRowId: root.selectedPreparationId
                loading: root.busy
                onRowSelected: function(rowId) { root.preparationSelected(String(rowId || "")) }
                onSortRequested: function(key, direction) { root.preparationSortRequested(key, direction) }
            }
        }
        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.preparations.total || 0) > Number(root.preparations.pageSize || 50)
            currentPage: Number(root.preparations.page || 1)
            pageSize: Number(root.preparations.pageSize || 50)
            totalItems: Number(root.preparations.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.preparationPageRequested(page) }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            visible: root.selectedPreparationId.length > 0
            title: root.selectedPreparation.title || "Selected Billing Preparation"
            ColumnLayout {
                width: parent ? parent.width : 0
                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    text: root.selectedPreparation.description || ""
                    color: Theme.AppTheme.textMuted
                    wrapMode: Text.WordWrap
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 900 ? 3 : (width >= 560 ? 2 : 1)
                    Repeater {
                        model: root.selectedPreparation.fields || []
                        delegate: ColumnLayout {
                            id: detailField
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.margins: Theme.AppTheme.spacingMd
                            AppControls.Label { text: String(detailField.modelData.label || ""); color: Theme.AppTheme.textMuted }
                            AppControls.Label { Layout.fillWidth: true; text: String(detailField.modelData.value || "-"); font.bold: true; wrapMode: Text.WordWrap }
                            AppControls.Label { Layout.fillWidth: true; text: String(detailField.modelData.supportingText || ""); color: Theme.AppTheme.textMuted; wrapMode: Text.WordWrap; visible: text.length > 0 }
                        }
                    }
                }
            }
        }

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Selected Preparation Lines" }
        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            visible: root.selectedPreparationId.length > 0
            searchText: root.lineSearch
            searchPlaceholder: "Search source, revision, task, resource, or description..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) {
                root.lineFiltersRequested(text, root._value(lineSourceTypeFilter, root._sourceTypes), root._value(lineSourceStateFilter, root._sourceStates))
            }
            AppControls.ComboBox {
                id: lineSourceTypeFilter
                implicitWidth: 165
                textRole: "label"
                model: root._sourceTypes
                currentIndex: root._indexOf(model, root.lineSourceType)
                onActivated: root.lineFiltersRequested(root.lineSearch, root._value(lineSourceTypeFilter, root._sourceTypes), root._value(lineSourceStateFilter, root._sourceStates))
            }
            AppControls.ComboBox {
                id: lineSourceStateFilter
                implicitWidth: 165
                textRole: "label"
                model: root._sourceStates
                currentIndex: root._indexOf(model, root.lineSourceState)
                onActivated: root.lineFiltersRequested(root.lineSearch, root._value(lineSourceTypeFilter, root._sourceTypes), root._value(lineSourceStateFilter, root._sourceStates))
            }
        }
        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.selectedPreparationId.length === 0 || (root.lines.items || []).length === 0
            title: root.selectedPreparationId.length === 0 ? "Select a Billing Preparation" : "No Preparation Lines"
            message: root.lines.emptyState || "Choose a preparation to load immutable source snapshots."
        }
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 290
            visible: root.selectedPreparationId.length > 0 && (root.lines.items || []).length > 0
            AppWidgets.DataTable {
                anchors.fill: parent
                objectName: "billingPreparationLinesTable"
                columns: root._lineColumns
                sourceModel: root.linesTableModel
                sortingMode: "server"
                sortKey: root.lineSortKey
                sortDirection: root.lineSortDirection
                loading: root.busy
                onSortRequested: function(key, direction) { root.lineSortRequested(key, direction) }
            }
        }
        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: root.selectedPreparationId.length > 0
                && Number(root.lines.total || 0) > Number(root.lines.pageSize || 50)
            currentPage: Number(root.lines.page || 1)
            pageSize: Number(root.lines.pageSize || 50)
            totalItems: Number(root.lines.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.linePageRequested(page) }
        }
    }
}
