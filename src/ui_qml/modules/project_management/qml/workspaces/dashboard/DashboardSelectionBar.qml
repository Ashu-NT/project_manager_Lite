import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectOptions: []
    property string selectedProjectId: ""
    property var baselineOptions: []
    property string selectedBaselineId: ""
    property var periodOptions: []
    property string selectedPeriodKey: ""
    property var viewOptions: []
    property string selectedViewKey: ""
    property bool isLoading: false

    signal projectSelected(string projectId)
    signal baselineSelected(string baselineId)
    signal periodSelected(string periodKey)
    signal viewSelected(string viewKey)
    signal refreshRequested()
    signal exportRequested()

    function indexForValue(options, selectedValue) {
        const rows = options || []
        for (let index = 0; index < rows.length; index += 1) {
            if (String(rows[index].value || "") === String(selectedValue || "")) {
                return index
            }
        }
        return rows.length > 0 ? 0 : -1
    }

    readonly property bool baselineSelectionLocked: (root.baselineOptions || []).length === 1
        && String(root.baselineOptions[0].label || "") === "Portfolio view"

    implicitHeight: toolbarColumn.implicitHeight

    ColumnLayout {
        id: toolbarColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingXs

        Rectangle {
            Layout.fillWidth: true
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1
            implicitHeight: contextRow.implicitHeight + (Theme.AppTheme.spacingSm * 2)

            RowLayout {
                id: contextRow

                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                anchors.topMargin: Theme.AppTheme.spacingSm
                anchors.bottomMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingSm

                Label {
                    text: "Scope"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                ComboBox {
                    Layout.preferredWidth: Math.max(220, root.width * 0.24)
                    Layout.fillWidth: true
                    enabled: !root.isLoading
                    model: root.projectOptions || []
                    textRole: "label"
                    currentIndex: root.indexForValue(root.projectOptions, root.selectedProjectId)

                    onActivated: function(index) {
                        const option = root.projectOptions[index]
                        root.projectSelected(String(option && option.value ? option.value : ""))
                    }
                }

                Label {
                    text: "Baseline"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                ComboBox {
                    Layout.preferredWidth: 210
                    enabled: !root.isLoading && !root.baselineSelectionLocked
                    model: root.baselineOptions || []
                    textRole: "label"
                    currentIndex: root.indexForValue(root.baselineOptions, root.selectedBaselineId)

                    onActivated: function(index) {
                        const option = root.baselineOptions[index]
                        root.baselineSelected(String(option && option.value ? option.value : ""))
                    }
                }

                Label {
                    text: "Period"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                ComboBox {
                    Layout.preferredWidth: 150
                    enabled: !root.isLoading
                    model: root.periodOptions || []
                    textRole: "label"
                    currentIndex: root.indexForValue(root.periodOptions, root.selectedPeriodKey)

                    onActivated: function(index) {
                        const option = root.periodOptions[index]
                        root.periodSelected(String(option && option.value ? option.value : ""))
                    }
                }

                Label {
                    text: "View"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                ComboBox {
                    Layout.preferredWidth: 190
                    enabled: !root.isLoading
                    model: root.viewOptions || []
                    textRole: "label"
                    currentIndex: root.indexForValue(root.viewOptions, root.selectedViewKey)

                    onActivated: function(index) {
                        const option = root.viewOptions[index]
                        root.viewSelected(String(option && option.value ? option.value : ""))
                    }
                }

                Item {
                    Layout.fillWidth: true
                }

                AppControls.SecondaryButton {
                    enabled: !root.isLoading
                    text: "Refresh"
                    iconName: "refresh"
                    onClicked: root.refreshRequested()
                }

                AppControls.SecondaryButton {
                    enabled: !root.isLoading
                    text: "Export"
                    iconName: "export"
                    onClicked: root.exportRequested()
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.baselineSelectionLocked
            text: "Portfolio overview keeps baseline selection locked and rolls up cross-project health."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}
