pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController
    property var intakeModel: ({ "emptyState": "No intake items are available yet.", "items": [] })
    property var intakeStatusOptions: []
    property string selectedIntakeStatusFilter: "all"
    property var fundingColumns: []
    property string selectedFundingId: ""

    function optionIndexForValue(options, value) {
        const opts = options || []
        for (let i = 0; i < opts.length; i += 1) {
            if (String(opts[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.intakeSearchText : ""
            searchPlaceholder: "Search intake by title or sponsor..."
            showRefresh: true
            showExport: false
            showFilter: true
            showCreate: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setIntakeSearchText(text)
            }
            onFilterClicked: filterPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                AppWidgets.DataTable {
                    id: _intakeTable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    multiSelect: false
                    columns: root.fundingColumns
                    sourceModel: root.workspaceController ? root.workspaceController.intakeItemsTableModel : null
                    emptyText: root.intakeModel.emptyState || "No intake items available."
                    selectedRowId: root.selectedFundingId

                    onRowSelected: function(rowId) { root.selectedFundingId = rowId }
                    onRowActivated: function(rowId) { root.selectedFundingId = rowId }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    visible: root.selectedFundingId.length > 0
                    color: Theme.AppTheme.surfaceAlt

                    Rectangle {
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 1
                        color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            text: "Status:"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }

                        AppControls.SecondaryButton {
                            text: "Approve"
                            iconName: "approve"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.updateIntakeItemStatus(root.selectedFundingId, "APPROVED")
                                    root.selectedFundingId = ""
                                }
                            }
                        }

                        AppControls.SecondaryButton {
                            text: "Review"
                            iconName: "edit"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.updateIntakeItemStatus(root.selectedFundingId, "REVIEW")
                                    root.selectedFundingId = ""
                                }
                            }
                        }

                        AppControls.SecondaryButton {
                            text: "Reject"
                            iconName: "delete"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.updateIntakeItemStatus(root.selectedFundingId, "REJECTED")
                                    root.selectedFundingId = ""
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        AppControls.SecondaryButton {
                            text: "Clear"
                            onClicked: root.selectedFundingId = ""
                        }
                    }
                }

                AppWidgets.TablePaginationBar {
                    Layout.fillWidth: true
                    currentPage: root.workspaceController ? root.workspaceController.intakePage : 1
                    pageSize: root.workspaceController ? root.workspaceController.intakePageSize : 25
                    totalItems: root.workspaceController ? root.workspaceController.intakeTotalCount : 0
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    onPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setIntakePage(page)
                    }
                    onPageSizeRequested: function(ps) {
                        if (root.workspaceController !== null) root.workspaceController.setIntakePageSize(ps)
                    }
                }
            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem
                width: 280
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

                    AppControls.Label {
                        text: "Intake Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.intakeStatusOptions || []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root.optionIndexForValue(
                            root.intakeStatusOptions || [],
                            root.selectedIntakeStatusFilter
                        )
                        onActivated: function(idx) {
                            const opts = root.intakeStatusOptions || []
                            if (root.workspaceController !== null && opts[idx])
                                root.workspaceController.setIntakeStatusFilter(String(opts[idx].value || "all"))
                        }
                    }

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        text: "Clear Filter"
                        iconName: "delete"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onClicked: {
                            if (root.workspaceController !== null)
                                root.workspaceController.setIntakeStatusFilter("all")
                            filterPopup.close()
                        }
                    }
                }
            }
        }
    }
}
