pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as PMControllers
import "OwnerTimesheetsColumnConfig.js" as ColumnConfig
import "components" as Components

Item {
    id: root

    property PMControllers.ProjectManagementWorkspaceCatalog pmCatalog
    readonly property PMControllers.ProjectManagementOwnerTimesheetsController workspaceController:
        root.pmCatalog ? root.pmCatalog.timesheetsWorkspace : null
    readonly property var period: root.workspaceController ? root.workspaceController.period : ({})
    property var selectedEntry: ({})

    function rowById(rowId) {
        const rows = root.workspaceController ? root.workspaceController.entries : []
        for (let i = 0; i < rows.length; i += 1) {
            if (String(rows[i].id || "") === String(rowId || "")) return rows[i]
        }
        return null
    }

    function openEntry(row) {
        root.selectedEntry = row || ({})
        entryDialog.prepare(root.selectedEntry)
        entryDialog.open()
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.workspaceBackground
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.PageHeader {
            Layout.fillWidth: true
            eyebrow: "Work"
            title: "Timesheets"
            subtitle: root.period.resourceName
                ? "Review and submit authoritative time for " + root.period.resourceName + "."
                : "Review and submit your recorded work."

            AppControls.SecondaryButton {
                text: "History"
                iconName: "history"
                enabled: root.period.ownerAvailable !== false
                    && (!root.workspaceController || !root.workspaceController.isBusy)
                onClicked: historyDialog.open()
            }

            AppControls.SecondaryButton {
                text: "Refresh"
                iconName: "refresh"
                enabled: root.workspaceController && !root.workspaceController.isBusy
                onClicked: root.workspaceController.refresh()
            }

            AppControls.PrimaryButton {
                text: root.period.canResubmit === true ? "Resubmit Timesheet" : "Submit Timesheet"
                iconName: "approve"
                visible: root.period.canSubmit === true
                enabled: root.workspaceController && !root.workspaceController.isBusy
                onClicked: submitConfirmation.open()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: periodRow.implicitHeight + Theme.AppTheme.spacingMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder

            RowLayout {
                id: periodRow
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingSm

                AppControls.SecondaryButton {
                    text: "Previous"
                    iconName: "chevron_left"
                    onClicked: if (root.workspaceController) root.workspaceController.shiftPeriod(-1)
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.period.periodLabel || "Current reporting period"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }
                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.period.statusLabel || "Loading"
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                AppControls.SecondaryButton {
                    text: "Current"
                    iconName: "calendar"
                    onClicked: if (root.workspaceController) root.workspaceController.selectCurrentPeriod()
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.period.ownerAvailable === false
            tone: "info"
            message: String(root.period.setupMessage || "Resource setup is required before time can be recorded.")
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.period.canViewReturnReason === true
            tone: "warning"
            message: "Returned for correction: " + String(root.period.returnReason || "No reason provided.")
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: [
                { "label": "Total Hours", "value": root.period.totalHoursLabel || "0.00 h" },
                { "label": "Entries", "value": String(root.period.entryCount || 0) },
                { "label": "Projects", "value": String(root.period.projectCount || 0) },
                { "label": "Tasks", "value": String(root.period.taskCount || 0) }
            ]
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search project, task, or description..."
            searchText: root.workspaceController ? root.workspaceController.entrySearchText : ""
            showCreate: root.period.canAddEntry === true
            createLabel: "Add Time Entry"
            showRefresh: false
            showCustomize: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            onSearchChanged: function(text) {
                if (root.workspaceController) root.workspaceController.setEntrySearchText(text)
            }
            onCreateRequested: root.openEntry(null)
            onCustomizeClicked: entriesTable.openColumnCustomizer(tableToolbar.customizeButtonItem)

            AppControls.ComboBox {
                width: 190
                model: root.workspaceController ? root.workspaceController.projectOptions : []
                textRole: "label"
                onActivated: function(index) {
                    const option = model[index]
                    if (root.workspaceController && option)
                        root.workspaceController.setProjectFilter(String(option.value || "all"))
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: entriesTable
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: entryPagination.top
                tableId: "pm.timesheets.owner.entries"
                columns: ColumnConfig.baseColumns()
                sourceModel: root.workspaceController ? root.workspaceController.entryTableModel : null
                sortingMode: "server"
                sortKey: root.workspaceController ? root.workspaceController.entrySortKey : "date"
                sortDirection: root.workspaceController ? root.workspaceController.entrySortDirection : Qt.DescendingOrder
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.workspaceController && root.workspaceController.entrySearchText
                    ? "No time entries match the current search."
                    : "No time has been recorded for this period."
                onSortRequested: function(key, direction) {
                    if (root.workspaceController) root.workspaceController.setEntrySort(key, direction)
                }
                onRowActivated: function(rowId) {
                    const row = root.rowById(rowId)
                    if (row && row.canEdit === true) root.openEntry(row)
                }
                onViewDetailRequested: function(rowId) {
                    const row = root.rowById(rowId)
                    if (row && row.canEdit === true) root.openEntry(row)
                }
            }

            AppWidgets.TablePaginationBar {
                id: entryPagination
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.entryPage : 1
                pageSize: root.workspaceController ? root.workspaceController.entryPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.entryTotal : 0
                busy: root.workspaceController ? root.workspaceController.isLoading : false
                onPageRequested: function(page) {
                    if (root.workspaceController) root.workspaceController.setEntryPage(page)
                }
                onPageSizeRequested: function(size) {
                    if (root.workspaceController) root.workspaceController.setEntryPageSize(size)
                }
            }
        }
    }

    Components.OwnerTimeEntryDialog {
        id: entryDialog
        assignmentOptions: root.workspaceController ? root.workspaceController.assignmentOptions : []
        defaultDate: root.period.periodStart || ""
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = root.workspaceController.saveEntry(payload)
            if (result.ok === true) entryDialog.close()
            else entryDialog.errorMessage = String(result.message || "The time entry could not be saved.")
        }
        onDestructiveRequested: deleteConfirmation.open()
    }

    AppControls.ConfirmationDialog {
        id: deleteConfirmation
        title: "Delete Time Entry"
        message: "Delete this recorded time entry?"
        supportingText: "Period and task totals will be recalculated from authoritative entries."
        confirmLabel: "Delete Entry"
        confirmIcon: "delete"
        confirmDanger: true
        onConfirmed: {
            if (!root.workspaceController) return
            const result = root.workspaceController.deleteEntry(String(root.selectedEntry.entryId || ""))
            if (result.ok === true) entryDialog.close()
        }
    }

    AppControls.ConfirmationDialog {
        id: submitConfirmation
        title: root.period.canResubmit === true ? "Resubmit Timesheet" : "Submit Timesheet"
        message: "Send " + String(root.period.periodLabel || "this period") + " for review?"
        supportingText: String(root.period.totalHoursLabel || "0.00 h") + " across "
            + String(root.period.entryCount || 0) + " entries. Editing is disabled while review is pending."
        confirmLabel: root.period.canResubmit === true ? "Resubmit" : "Submit"
        confirmIcon: "approve"
        onConfirmed: if (root.workspaceController) root.workspaceController.submitPeriod("")
    }

    Components.OwnerTimesheetHistoryDialog {
        id: historyDialog
        workspaceController: root.workspaceController
    }
}
