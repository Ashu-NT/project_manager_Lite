pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var selectedForecast: ({ "id": "", "fields": [], "emptyState": "" })
    property var forecastVersions: ({ "items": [] })
    property var forecastLines: ({ "items": [] })
    property var versionsTableModel: null
    property var linesTableModel: null
    property string selectedForecastId: ""
    property string versionSortKey: "revision"
    property int versionSortDirection: Qt.DescendingOrder
    property string lineSortKey: "title"
    property int lineSortDirection: Qt.AscendingOrder
    property string versionSearch: ""
    property string versionStatus: ""
    property string generationMode: ""
    property string lineSearch: ""
    property string lineSourceType: ""
    property bool isBusy: false

    signal forecastSelected(string forecastId)
    signal versionPageRequested(int page)
    signal linePageRequested(int page)
    signal versionSortRequested(string key, int direction)
    signal lineSortRequested(string key, int direction)
    signal versionFiltersRequested(string search, string status, string generationMode)
    signal lineFiltersRequested(string search, string sourceType)

    readonly property var _versionColumns: [
        { "key": "title", "label": "Forecast", "flex": 1.5, "sortable": true },
        { "key": "statusLabel", "label": "Status", "minWidth": 105, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "As of / generation", "flex": 1.4, "sortable": true },
        { "key": "supportingText", "label": "ETC / lines", "flex": 1.4, "sortable": true },
        { "key": "metaText", "label": "Approval / version", "flex": 1.5, "sortable": true }
    ]
    readonly property var _lineColumns: [
        { "key": "title", "label": "Description", "flex": 1.6, "sortable": true },
        { "key": "subtitle", "label": "Cost code / task", "flex": 1.4, "sortable": true },
        { "key": "statusLabel", "label": "Origin", "minWidth": 100, "flex": 0, "sortable": true },
        { "key": "supportingText", "label": "Amount / source", "flex": 1.5, "sortable": true },
        { "key": "metaText", "label": "Period / evidence", "flex": 1.8, "sortable": true }
    ]
    readonly property var _statusOptions: [
        { "value": "", "label": "All statuses" },
        { "value": "draft", "label": "Draft" },
        { "value": "submitted", "label": "Submitted" },
        { "value": "approved", "label": "Approved" },
        { "value": "rejected", "label": "Rejected" },
        { "value": "superseded", "label": "Superseded" }
    ]
    readonly property var _generationOptions: [
        { "value": "", "label": "All generation modes" },
        { "value": "automatic", "label": "Automatic" },
        { "value": "manual", "label": "Manual" },
        { "value": "hybrid", "label": "Hybrid" }
    ]
    readonly property var _sourceOptions: [
        { "value": "", "label": "All source types" },
        { "value": "remaining_plan", "label": "Remaining plan" },
        { "value": "open_commitment", "label": "Open commitment" },
        { "value": "risk", "label": "Risk contingency" },
        { "value": "manual_estimate", "label": "Manual estimate" },
        { "value": "base_forecast", "label": "Base forecast" },
        { "value": "financial_change", "label": "Financial change" }
    ]

    function _indexOf(model, value) {
        for (let index = 0; index < model.length; index += 1) {
            if (String(model[index].value) === String(value || "")) return index
        }
        return 0
    }

    function _versionFilters() {
        const status = root._statusOptions[statusFilter.currentIndex]
        const generation = root._generationOptions[generationFilter.currentIndex]
        root.versionFiltersRequested(
            root.versionSearch,
            status ? String(status.value) : "",
            generation ? String(generation.value) : ""
        )
    }

    function _lineFilters() {
        const source = root._sourceOptions[sourceFilter.currentIndex]
        root.lineFiltersRequested(
            root.lineSearch,
            source ? String(source.value) : ""
        )
    }

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Forecast Versions"
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.versionSearch
            searchPlaceholder: "Search forecast name, notes, or creator..."
            showFilter: false
            showRefresh: false
            isBusy: root.isBusy
            onSearchChanged: function(text) {
                const status = root._statusOptions[statusFilter.currentIndex]
                const generation = root._generationOptions[generationFilter.currentIndex]
                root.versionFiltersRequested(
                    text,
                    status ? String(status.value) : "",
                    generation ? String(generation.value) : ""
                )
            }

            AppControls.ComboBox {
                id: statusFilter
                implicitWidth: 145
                textRole: "label"
                model: root._statusOptions
                currentIndex: root._indexOf(root._statusOptions, root.versionStatus)
                onActivated: root._versionFilters()
            }

            AppControls.ComboBox {
                id: generationFilter
                implicitWidth: 190
                textRole: "label"
                model: root._generationOptions
                currentIndex: root._indexOf(root._generationOptions, root.generationMode)
                onActivated: root._versionFilters()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.forecastVersions.items || []).length === 0
            title: "No forecast versions"
            message: root.forecastVersions.emptyState || "No forecasts match the current filters."
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 250
            visible: (root.forecastVersions.items || []).length > 0

            AppWidgets.DataTable {
                objectName: "forecastVersionsTable"
                anchors.fill: parent
                columns: root._versionColumns
                sourceModel: root.versionsTableModel
                sortingMode: "server"
                sortKey: root.versionSortKey
                sortDirection: root.versionSortDirection
                selectedRowId: root.selectedForecastId
                loading: root.isBusy
                emptyText: root.forecastVersions.emptyState || "No forecast versions."
                onRowSelected: function(rowId) {
                    root.forecastSelected(String(rowId || ""))
                }
                onSortRequested: function(key, direction) {
                    root.versionSortRequested(key, direction)
                }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.forecastVersions.total || 0)
                > Number(root.forecastVersions.pageSize || 50)
            currentPage: Number(root.forecastVersions.page || 1)
            pageSize: Number(root.forecastVersions.pageSize || 50)
            totalItems: Number(root.forecastVersions.total || 0)
            busy: root.isBusy
            onPageRequested: function(page) { root.versionPageRequested(page) }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            visible: String(root.selectedForecast.id || "").length > 0
            title: root.selectedForecast.title || "Selected Forecast"

            ColumnLayout {
                width: parent ? parent.width : 0
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    Layout.bottomMargin: 0
                    text: (root.selectedForecast.statusLabel || "")
                        + " | " + (root.selectedForecast.subtitle || "")
                    color: Theme.AppTheme.textSecondary
                    wrapMode: Text.WordWrap
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    columns: width >= 900 ? 3 : (width >= 560 ? 2 : 1)
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root.selectedForecast.fields || []
                        delegate: ColumnLayout {
                            id: detailField
                            required property var modelData
                            Layout.fillWidth: true
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(detailField.modelData.label || "")
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(detailField.modelData.value || "-")
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.selectedForecastId.length === 0
            title: "Select a Forecast Version"
            message: root.selectedForecast.emptyState
                || "Choose a version above to inspect its authoritative ETC lines."
        }

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            visible: root.selectedForecastId.length > 0
            label: "Selected Forecast Lines"
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            visible: root.selectedForecastId.length > 0
            searchText: root.lineSearch
            searchPlaceholder: "Search description, cost code, task, or source..."
            showFilter: false
            showRefresh: false
            isBusy: root.isBusy
            onSearchChanged: function(text) {
                const source = root._sourceOptions[sourceFilter.currentIndex]
                root.lineFiltersRequested(
                    text,
                    source ? String(source.value) : ""
                )
            }

            AppControls.ComboBox {
                id: sourceFilter
                implicitWidth: 180
                textRole: "label"
                model: root._sourceOptions
                currentIndex: root._indexOf(root._sourceOptions, root.lineSourceType)
                onActivated: root._lineFilters()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.selectedForecastId.length > 0
                && (root.forecastLines.items || []).length === 0
            title: "No forecast lines"
            message: root.forecastLines.emptyState || "No lines match the current filters."
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 290
            visible: root.selectedForecastId.length > 0
                && (root.forecastLines.items || []).length > 0

            AppWidgets.DataTable {
                objectName: "forecastLinesTable"
                anchors.fill: parent
                columns: root._lineColumns
                sourceModel: root.linesTableModel
                sortingMode: "server"
                sortKey: root.lineSortKey
                sortDirection: root.lineSortDirection
                loading: root.isBusy
                emptyText: root.forecastLines.emptyState || "No forecast lines."
                onSortRequested: function(key, direction) {
                    root.lineSortRequested(key, direction)
                }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: root.selectedForecastId.length > 0
                && Number(root.forecastLines.total || 0)
                    > Number(root.forecastLines.pageSize || 50)
            currentPage: Number(root.forecastLines.page || 1)
            pageSize: Number(root.forecastLines.pageSize || 50)
            totalItems: Number(root.forecastLines.total || 0)
            busy: root.isBusy
            onPageRequested: function(page) { root.linePageRequested(page) }
        }
    }
}
