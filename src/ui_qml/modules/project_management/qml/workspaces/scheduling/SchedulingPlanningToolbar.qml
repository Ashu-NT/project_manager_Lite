pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var projectOptions: []
    property var baselineOptions: []
    property var calendarOptions: []
    property string selectedProjectId: ""
    property string selectedBaselineId: ""
    property string selectedCalendarId: "default"
    property string searchText: ""
    property bool isBusy: false

    signal projectSelected(string projectId)
    signal baselineSelected(string baselineId)
    signal calendarSelected(string calendarId)
    signal searchChanged(string text)
    signal filterRequested()
    signal refreshRequested()
    signal saveBaselineRequested()
    signal recalculateRequested()
    signal exportRequested()

    function _indexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return optionList.length > 0 ? 0 : -1
    }

    implicitHeight: Theme.AppTheme.toolbarHeight + 2
    color: Theme.AppTheme.surfaceRaised
    radius: Theme.AppTheme.radiusMd

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        ComboBox {
            Layout.preferredWidth: 210
            model: root.projectOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(root.projectOptions, root.selectedProjectId)

            onActivated: function(index) {
                const option = root.projectOptions[index]
                if (option) {
                    root.projectSelected(String(option.value || ""))
                }
            }
        }

        ComboBox {
            Layout.preferredWidth: 190
            model: root.baselineOptions
            textRole: "label"
            enabled: !root.isBusy && root.baselineOptions.length > 0
            currentIndex: root._indexForValue(root.baselineOptions, root.selectedBaselineId)

            onActivated: function(index) {
                const option = root.baselineOptions[index]
                if (option) {
                    root.baselineSelected(String(option.value || ""))
                }
            }
        }

        ComboBox {
            Layout.preferredWidth: 170
            model: root.calendarOptions
            textRole: "label"
            enabled: !root.isBusy && root.calendarOptions.length > 0
            currentIndex: root._indexForValue(root.calendarOptions, root.selectedCalendarId)

            onActivated: function(index) {
                const option = root.calendarOptions[index]
                if (option) {
                    root.calendarSelected(String(option.value || ""))
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Theme.AppTheme.inputHeight
            radius: Theme.AppTheme.radiusSm
            color: Theme.AppTheme.surface
            border.color: searchField.activeFocus
                ? Theme.AppTheme.focusBorder
                : Theme.AppTheme.subtleBorder
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingSm
                anchors.rightMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "search"
                    size: 12
                    iconColor: Theme.AppTheme.textMuted
                }

                TextField {
                    id: searchField
                    Layout.fillWidth: true
                    placeholderText: "Search activities..."
                    enabled: !root.isBusy
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    color: Theme.AppTheme.textPrimary
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
                    background: Item {}

                    Timer {
                        id: _debounce
                        interval: 260
                        onTriggered: root.searchChanged(searchField.text)
                    }

                    onTextChanged: _debounce.restart()
                    Keys.onReturnPressed: {
                        _debounce.stop()
                        root.searchChanged(searchField.text)
                    }
                }
            }
        }

        Rectangle {
            implicitWidth: filterRow.implicitWidth + 14
            implicitHeight: Theme.AppTheme.inputHeight - 4
            radius: Theme.AppTheme.radiusSm
            color: filterHover.containsMouse
                ? Theme.AppTheme.hoverSurface
                : Theme.AppTheme.surfaceOverlay

            Row {
                id: filterRow
                anchors.centerIn: parent
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "filter"
                    size: 11
                    iconColor: Theme.AppTheme.textMuted
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Filters"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                id: filterHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.filterRequested()
            }
        }

        AppControls.SecondaryButton {
            text: "Refresh"
            iconName: "refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }

        AppControls.SecondaryButton {
            text: "Export"
            iconName: "export"
            enabled: !root.isBusy
            onClicked: root.exportRequested()
        }

        AppControls.SecondaryButton {
            text: "Save Baseline"
            iconName: "register"
            enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
            onClicked: root.saveBaselineRequested()
        }

        AppControls.PrimaryButton {
            text: "Recalculate"
            iconName: "approve"
            enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
            onClicked: root.recalculateRequested()
        }
    }

    onSearchTextChanged: {
        if (searchField.text !== root.searchText) {
            searchField.text = root.searchText
        }
    }

    Component.onCompleted: {
        if (searchField.text !== root.searchText) {
            searchField.text = root.searchText
        }
    }
}
