pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var cards: ({ "title": "Rate Cards", "emptyState": "", "items": [] })
    property var lines: ({ "title": "Rate Card Lines", "emptyState": "", "items": [] })
    property var selectedCard: ({ "id": "", "fields": [] })
    property var cardsTableModel: null
    property var linesTableModel: null
    property string selectedCardId: ""
    property string cardSortKey: "title"
    property int cardSortDirection: Qt.AscendingOrder
    property string lineSortKey: "title"
    property int lineSortDirection: Qt.AscendingOrder
    property string cardSearch: ""
    property string cardScope: ""
    property string cardStatus: ""
    property string lineSearch: ""
    property string lineRateType: ""
    property string lineStatus: ""
    property string lineEffectiveStatus: ""
    property bool busy: false

    signal cardSelected(string rateCardId)
    signal cardPageRequested(int page)
    signal linePageRequested(int page)
    signal cardSortRequested(string key, int direction)
    signal lineSortRequested(string key, int direction)
    signal cardFiltersRequested(string search, string scope, string status)
    signal lineFiltersRequested(string search, string rateType, string status, string effectiveStatus)

    readonly property var _cardColumns: [
        { "key": "title", "label": "Rate Card", "flex": 1.7, "sortable": true },
        { "key": "subtitle", "label": "Scope", "minWidth": 130, "flex": 0, "sortable": true },
        { "key": "statusLabel", "label": "Status", "minWidth": 100, "flex": 0, "sortable": true },
        { "key": "supportingText", "label": "Lines", "minWidth": 120, "flex": 0, "sortable": true },
        { "key": "metaText", "label": "Origin / version", "flex": 1.2, "sortable": true }
    ]
    readonly property var _lineColumns: [
        { "key": "title", "label": "Applies To", "flex": 1.5, "sortable": true },
        { "key": "statusLabel", "label": "Purpose", "minWidth": 95, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "Rate", "flex": 1.2, "sortable": true },
        { "key": "supportingText", "label": "Effective", "flex": 1.6, "sortable": true },
        { "key": "metaText", "label": "Origin / modifiers", "flex": 1.5, "sortable": true }
    ]
    readonly property var _scopeOptions: [
        { "value": "", "label": "All scopes" },
        { "value": "organization", "label": "Organization" },
        { "value": "project", "label": "Project" }
    ]
    readonly property var _statusOptions: [
        { "value": "", "label": "All statuses" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _typeOptions: [
        { "value": "", "label": "All purposes" },
        { "value": "cost", "label": "Cost" },
        { "value": "billing", "label": "Billing" }
    ]
    readonly property var _effectiveOptions: [
        { "value": "", "label": "All dates" },
        { "value": "current", "label": "Current" },
        { "value": "future", "label": "Future" },
        { "value": "expired", "label": "Expired" },
        { "value": "open_ended", "label": "Open-ended" }
    ]

    function _indexOf(model, value) {
        for (let index = 0; index < model.length; index += 1) {
            if (String(model[index].value) === String(value || "")) return index
        }
        return 0
    }

    function _cardFilters() {
        const scope = root._scopeOptions[scopeFilter.currentIndex]
        const status = root._statusOptions[cardStatusFilter.currentIndex]
        root.cardFiltersRequested(root.cardSearch,
                                  scope ? String(scope.value) : "",
                                  status ? String(status.value) : "")
    }

    function _lineFilters() {
        const type = root._typeOptions[typeFilter.currentIndex]
        const status = root._statusOptions[lineStatusFilter.currentIndex]
        const effective = root._effectiveOptions[effectiveFilter.currentIndex]
        root.lineFiltersRequested(root.lineSearch,
                                  type ? String(type.value) : "",
                                  status ? String(status.value) : "",
                                  effective ? String(effective.value) : "")
    }

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Rate Cards" }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.cardSearch
            searchPlaceholder: "Search Rate Cards..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) {
                const scope = root._scopeOptions[scopeFilter.currentIndex]
                const status = root._statusOptions[cardStatusFilter.currentIndex]
                root.cardFiltersRequested(text,
                                          scope ? String(scope.value) : "",
                                          status ? String(status.value) : "")
            }
            AppControls.ComboBox {
                id: scopeFilter
                implicitWidth: 155
                textRole: "label"
                model: root._scopeOptions
                currentIndex: root._indexOf(root._scopeOptions, root.cardScope)
                onActivated: root._cardFilters()
            }
            AppControls.ComboBox {
                id: cardStatusFilter
                implicitWidth: 140
                textRole: "label"
                model: root._statusOptions
                currentIndex: root._indexOf(root._statusOptions, root.cardStatus)
                onActivated: root._cardFilters()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.cards.items || []).length === 0
            title: "No Rate Cards"
            message: root.cards.emptyState || "No Rate Cards match the current filters."
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 250
            visible: (root.cards.items || []).length > 0
            AppWidgets.DataTable {
                objectName: "rateCardsTable"
                anchors.fill: parent
                columns: root._cardColumns
                sourceModel: root.cardsTableModel
                sortingMode: "server"
                sortKey: root.cardSortKey
                sortDirection: root.cardSortDirection
                selectedRowId: root.selectedCardId
                loading: root.busy
                emptyText: root.cards.emptyState || "No Rate Cards."
                onRowSelected: function(rowId) { root.cardSelected(String(rowId || "")) }
                onSortRequested: function(key, direction) { root.cardSortRequested(key, direction) }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.cards.total || 0) > Number(root.cards.pageSize || 50)
            currentPage: Number(root.cards.page || 1)
            pageSize: Number(root.cards.pageSize || 50)
            totalItems: Number(root.cards.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.cardPageRequested(page) }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            visible: String(root.selectedCard.id || "").length > 0
            title: root.selectedCard.title || "Selected Rate Card"
            GridLayout {
                width: parent ? parent.width : 0
                columns: width >= 900 ? 3 : (width >= 560 ? 2 : 1)
                columnSpacing: Theme.AppTheme.spacingLg
                rowSpacing: Theme.AppTheme.spacingSm
                Repeater {
                    model: root.selectedCard.fields || []
                    delegate: ColumnLayout {
                        id: detailField
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.margins: Theme.AppTheme.spacingMd
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

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Selected Rate Card Lines" }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            visible: root.selectedCardId.length > 0
            searchText: root.lineSearch
            searchPlaceholder: "Search resource, role, skill, department, or currency..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) {
                const type = root._typeOptions[typeFilter.currentIndex]
                const status = root._statusOptions[lineStatusFilter.currentIndex]
                const effective = root._effectiveOptions[effectiveFilter.currentIndex]
                root.lineFiltersRequested(text,
                                          type ? String(type.value) : "",
                                          status ? String(status.value) : "",
                                          effective ? String(effective.value) : "")
            }
            AppControls.ComboBox {
                id: typeFilter
                implicitWidth: 145
                textRole: "label"
                model: root._typeOptions
                currentIndex: root._indexOf(root._typeOptions, root.lineRateType)
                onActivated: root._lineFilters()
            }
            AppControls.ComboBox {
                id: lineStatusFilter
                implicitWidth: 140
                textRole: "label"
                model: root._statusOptions
                currentIndex: root._indexOf(root._statusOptions, root.lineStatus)
                onActivated: root._lineFilters()
            }
            AppControls.ComboBox {
                id: effectiveFilter
                implicitWidth: 145
                textRole: "label"
                model: root._effectiveOptions
                currentIndex: root._indexOf(root._effectiveOptions, root.lineEffectiveStatus)
                onActivated: root._lineFilters()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.selectedCardId.length === 0 || (root.lines.items || []).length === 0
            title: root.selectedCardId.length === 0 ? "Select a Rate Card" : "No Rate Card Lines"
            message: root.selectedCardId.length === 0
                ? "Choose a Rate Card above to load its effective-dated lines."
                : (root.lines.emptyState || "No Rate Card Lines match the current filters.")
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 290
            visible: root.selectedCardId.length > 0 && (root.lines.items || []).length > 0
            AppWidgets.DataTable {
                objectName: "rateLinesTable"
                anchors.fill: parent
                columns: root._lineColumns
                sourceModel: root.linesTableModel
                sortingMode: "server"
                sortKey: root.lineSortKey
                sortDirection: root.lineSortDirection
                loading: root.busy
                emptyText: root.lines.emptyState || "No Rate Card Lines."
                onSortRequested: function(key, direction) { root.lineSortRequested(key, direction) }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: root.selectedCardId.length > 0
                && Number(root.lines.total || 0) > Number(root.lines.pageSize || 50)
            currentPage: Number(root.lines.page || 1)
            pageSize: Number(root.lines.pageSize || 50)
            totalItems: Number(root.lines.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.linePageRequested(page) }
        }
    }
}
