pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // Task-scoped (every assignment on this task), all-time Time Entries
    // page straight from TaskTimeEntriesPageDesktopDto (docs §44 Time
    // redesign) -- authoritative server-side paging, never a locally
    // filtered slice of a truncated dataset.
    property var taskTimeEntriesPage: ({ "items": [], "total": 0, "page": 1, "pageSize": 25 })
    property var entriesTableModel: null
    property var resourceOptions: []
    property string resourceFilter: ""
    property string selectedEntryId: ""
    property bool isBusy: false

    signal entrySelected(string entryId)
    signal resourceFilterRequested(string resourceId)
    signal pageRequested(int page)

    readonly property var _page: root.taskTimeEntriesPage || {}
    readonly property var _items: root._page.items || []
    readonly property int _total: root._page.total || 0
    readonly property int _currentPage: root._page.page || 1
    readonly property int _pageSize: root._page.pageSize || 25
    readonly property var _columns: [
        { key: "entryDateLabel", label: "Date", flex: 1, minWidth: 100 },
        { key: "resourceName", label: "Resource", flex: 1, minWidth: 140 },
        { key: "hoursLabel", label: "Hours", flex: 0, minWidth: 80 },
        { key: "note", label: "Description", flex: 3, minWidth: 200 }
    ]
    readonly property int _tableH: {
        const count = root._items.length
        const natural = Theme.AppTheme.normalRowHeight + Math.max(count, 1) * Theme.AppTheme.compactRowHeight + 24
        return Math.max(240, Math.min(natural, 420))
    }

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
                        text: "Time Entries"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "The authoritative individual records making up this task's actual time."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }

                ColumnLayout {
                    spacing: 2

                    AppControls.Label {
                        text: "Resource"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    AppControls.ComboBox {
                        implicitWidth: 180
                        model: [{ "value": "", "label": "All" }].concat(root.resourceOptions)
                        textRole: "label"
                        enabled: !root.isBusy
                        currentIndex: {
                            const options = [{ "value": "" }].concat(root.resourceOptions)
                            for (let i = 0; i < options.length; i += 1) {
                                if (String(options[i].value || "") === root.resourceFilter)
                                    return i
                            }
                            return 0
                        }
                        onActivated: function(index) {
                            const options = [{ "value": "" }].concat(root.resourceOptions)
                            const option = options[index]
                            root.resourceFilterRequested(option ? String(option.value || "") : "")
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
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
                    emptyText: "No time entries recorded for this task yet."

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
                    ? "Select a row to edit or delete it in Log Time."
                    : "Entries will appear here once time is logged for this task."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }

            AppWidgets.TablePaginationBar {
                Layout.fillWidth: true
                currentPage: root._currentPage
                pageSize: root._pageSize
                totalItems: root._total
                busy: root.isBusy
                onPageRequested: function(page) { root.pageRequested(page) }
            }
        }
    }
}
