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
    property var dependenciesModel: ({ "emptyState": "No cross-project dependencies recorded.", "items": [] })
    property var riskColumns: []
    property string selectedDependencyId: ""

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.dependencySearchText : ""
            searchPlaceholder: "Search dependencies by project or summary..."
            showRefresh: true
            showExport: false
            showFilter: false
            showCreate: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setDependencySearchText(text)
            }
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
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    multiSelect: false
                    columns: root.riskColumns
                    sourceModel: root.workspaceController ? root.workspaceController.portfolioDependenciesTableModel : null
                    emptyText: root.dependenciesModel.emptyState || "No cross-project dependencies recorded."
                    selectedRowId: root.selectedDependencyId

                    onRowSelected: function(rowId) { root.selectedDependencyId = rowId }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    visible: root.selectedDependencyId.length > 0
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

                        Item { Layout.fillWidth: true }

                        AppControls.SecondaryButton {
                            text: "Remove"
                            iconName: "delete"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.removeDependency(root.selectedDependencyId)
                                    root.selectedDependencyId = ""
                                }
                            }
                        }

                        AppControls.SecondaryButton {
                            text: "Clear"
                            onClicked: root.selectedDependencyId = ""
                        }
                    }
                }

                AppWidgets.TablePaginationBar {
                    Layout.fillWidth: true
                    currentPage: root.workspaceController ? root.workspaceController.dependencyPage : 1
                    pageSize: root.workspaceController ? root.workspaceController.dependencyPageSize : 25
                    totalItems: root.workspaceController ? root.workspaceController.dependencyTotalCount : 0
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    onPageRequested: function(page) {
                        if (root.workspaceController !== null) root.workspaceController.setDependencyPage(page)
                    }
                    onPageSizeRequested: function(ps) {
                        if (root.workspaceController !== null) root.workspaceController.setDependencyPageSize(ps)
                    }
                }
            }
        }
    }
}
