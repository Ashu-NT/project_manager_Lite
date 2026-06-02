pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var workspaceController: null
    property var activityColumns: []
    property string activityTableId: "pm.scheduling.activity.table"
    property var timelineModel: ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })

    signal activityColumnsChanged(var cols)
    signal activityDetailRequested(string activityId)

    function _buildColumnState(columns) {
        const order = []
        const hidden = []
        for (let i = 0; i < columns.length; i++) {
            order.push(columns[i].key)
            if (columns[i].visible === false) hidden.push(columns[i].key)
        }
        return { "columnOrder": order, "hiddenColumns": hidden }
    }

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Activity & Timeline"
        subtitle: "Primary planning console with filtered activities and the current timeline lane."

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            AppWidgets.TableToolbar {
                id: activityToolbar
                Layout.fillWidth: true
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                searchPlaceholder: "Search activities..."
                showFilter: true
                showCustomize: true
                showExport: true
                showRefresh: false
                showViews: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchChanged: function(text) {
                    if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                }
                onFilterClicked: activityFilterPopup.open()
                onCustomizeClicked: activityTable.openColumnCustomizer(activityToolbar.customizeButtonItem)
                onExportRequested: {
                    if (root.workspaceController !== null) root.workspaceController.exportSchedule()
                }
            }

            SplitView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                orientation: Qt.Horizontal

                Item {
                    SplitView.minimumWidth: 420
                    SplitView.preferredWidth: 560
                    SplitView.fillHeight: true

                    AppWidgets.DataTable {
                        id: activityTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: activityPagination.top
                        tableId: root.activityTableId
                        columns: root.activityColumns
                        sourceModel: root.workspaceController ? root.workspaceController.scheduleTableModel : null
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.workspaceController ? (root.workspaceController.schedule.emptyState || "No activities are available for the selected planning scope.") : "No activities are available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedActivityId : ""
                        onColumnsStateChanged: function(cols) {
                            if (root.workspaceController)
                                root.workspaceController.saveTableColumnState(root.activityTableId, root._buildColumnState(cols))
                            root.activityColumnsChanged(cols)
                        }
                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectActivity(rowId)
                        }
                        onRowActivated: function(rowId) {
                            root.activityDetailRequested(rowId)
                        }
                    }

                    AppWidgets.TablePaginationBar {
                        id: activityPagination
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root.workspaceController ? root.workspaceController.activityPage : 1
                        pageSize: root.workspaceController ? root.workspaceController.activityPageSize : 25
                        totalItems: root.workspaceController ? root.workspaceController.activityTotalCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setActivityPage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null) root.workspaceController.setActivityPageSize(pageSize)
                        }
                    }

                    AppWidgets.AnchoredPopup {
                        id: activityFilterPopup
                        anchorItem: activityToolbar.filterButtonItem
                        width: 288
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label { text: "Filters"; font.bold: true; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; color: Theme.AppTheme.textMuted }
                            AppControls.Label { text: "Status"; font.bold: true; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; color: Theme.AppTheme.textMuted }

                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndex(
                                    root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                )
                                onActivated: function(index) {
                                    const options = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                    if (root.workspaceController !== null && options[index])
                                        root.workspaceController.setStatusFilter(String(options[index].value || "all"))
                                }
                            }

                            AppControls.CheckBox {
                                text: "Critical only"
                                checked: root.workspaceController ? root.workspaceController.showCriticalOnly : false
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onToggled: {
                                    if (root.workspaceController !== null) root.workspaceController.setShowCriticalOnly(checked)
                                }
                            }

                            AppControls.CheckBox {
                                text: "Delayed only"
                                checked: root.workspaceController ? root.workspaceController.showDelayedOnly : false
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onToggled: {
                                    if (root.workspaceController !== null) root.workspaceController.setShowDelayedOnly(checked)
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Clear"
                                    iconName: "close"
                                    onClicked: {
                                        if (root.workspaceController !== null) root.workspaceController.clearFilters()
                                        activityFilterPopup.close()
                                    }
                                }

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text: "Done"
                                    iconName: "approve"
                                    onClicked: activityFilterPopup.close()
                                }
                            }
                        }
                    }
                }

                SchedulingTimelinePanel {
                    SplitView.minimumWidth: 420
                    SplitView.preferredWidth: 760
                    SplitView.fillWidth: true
                    SplitView.fillHeight: true
                    timelineModel: root.timelineModel
                }
            }
        }
    }
}
