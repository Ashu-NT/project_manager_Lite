pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var workspaceController: null
    property var state: null

    // Draft selections, staged until Apply commits them to the controller.
    // Date fields are read directly from their own `id.text` at Apply time
    // (matching TimesheetsFilterPopup's pattern) rather than round-tripped
    // through a JS property, which would risk a binding loop against the
    // field's own `text:` binding.
    property string _draftStatus: "all"
    property string _draftSite: "all"
    property string _draftDepartment: "all"
    property string _draftManager: "all"

    readonly property var _siteOptions: [{ "value": "all", "label": "All Sites" }].concat(
        root.workspaceController ? (root.workspaceController.siteOptions || []) : [])
    readonly property var _departmentOptions: [{ "value": "all", "label": "All Departments" }].concat(
        root.workspaceController ? (root.workspaceController.departmentOptions || []) : [])
    readonly property var _managerOptions: [{ "value": "all", "label": "All Managers" }].concat(
        root.workspaceController ? (root.workspaceController.managerOptions || []) : [])

    title: "Filter Projects"
    width: 380
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    function _optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    onAboutToShow: {
        const c = root.workspaceController
        root._draftStatus = c ? c.selectedStatusFilter : "all"
        root._draftSite = c ? c.selectedSiteFilter : "all"
        root._draftDepartment = c ? c.selectedDepartmentFilter : "all"
        root._draftManager = c ? c.selectedManagerFilter : "all"
        startFromField.text = c ? c.startDateFrom : ""
        startToField.text = c ? c.startDateTo : ""
        endFromField.text = c ? c.endDateFrom : ""
        endToField.text = c ? c.endDateTo : ""
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

        // Two-column layout at the dialog's own width keeps this filter
        // surface landscape (wide, not tall) despite carrying seven fields.
        GridLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            columns: root.width > 340 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Status"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                    textRole: "label"
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    currentIndex: root.state ? root.state.statusIndexForValue(root._draftStatus) : 0
                    onActivated: function(index) {
                        const opt = root.workspaceController
                            ? (root.workspaceController.statusOptions || [])[index]
                            : null
                        root._draftStatus = String((opt && opt.value) || "all")
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Site"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: root._siteOptions
                    textRole: "label"
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    currentIndex: root._optionIndexForValue(root._siteOptions, root._draftSite)
                    onActivated: function(index) {
                        root._draftSite = String((root._siteOptions[index] && root._siteOptions[index].value) || "all")
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Department"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: root._departmentOptions
                    textRole: "label"
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    currentIndex: root._optionIndexForValue(root._departmentOptions, root._draftDepartment)
                    onActivated: function(index) {
                        root._draftDepartment = String((root._departmentOptions[index] && root._departmentOptions[index].value) || "all")
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Project Manager"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }
                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: root._managerOptions
                    textRole: "label"
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    currentIndex: root._optionIndexForValue(root._managerOptions, root._draftManager)
                    onActivated: function(index) {
                        root._draftManager = String((root._managerOptions[index] && root._managerOptions[index].value) || "all")
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.columnSpan: parent.columns
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Start Date Range"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.DateField {
                        id: startFromField
                        Layout.fillWidth: true
                        placeholderText: "From"
                        popupBoundaryItem: root.contentItem
                    }
                    AppControls.DateField {
                        id: startToField
                        Layout.fillWidth: true
                        placeholderText: "To"
                        popupBoundaryItem: root.contentItem
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.columnSpan: parent.columns
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "End Date Range"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.DateField {
                        id: endFromField
                        Layout.fillWidth: true
                        placeholderText: "From"
                        popupBoundaryItem: root.contentItem
                    }
                    AppControls.DateField {
                        id: endToField
                        Layout.fillWidth: true
                        placeholderText: "To"
                        popupBoundaryItem: root.contentItem
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Clear all"
                iconName: "refresh"
                onClicked: {
                    if (root.workspaceController !== null)
                        root.workspaceController.clearFilters()
                    root.close()
                }
            }
            Item { Layout.fillWidth: true }
            AppControls.SecondaryButton {
                text: "Close"
                iconName: "close"
                onClicked: root.close()
            }
            AppControls.PrimaryButton {
                text: "Apply"
                iconName: "approve"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStatusFilter(root._draftStatus)
                        root.workspaceController.setSiteFilter(root._draftSite)
                        root.workspaceController.setDepartmentFilter(root._draftDepartment)
                        root.workspaceController.setManagerFilter(root._draftManager)
                        root.workspaceController.setStartDateFrom(startFromField.text)
                        root.workspaceController.setStartDateTo(startToField.text)
                        root.workspaceController.setEndDateFrom(endFromField.text)
                        root.workspaceController.setEndDateTo(endToField.text)
                    }
                    root.close()
                }
            }
        }
    }
}
