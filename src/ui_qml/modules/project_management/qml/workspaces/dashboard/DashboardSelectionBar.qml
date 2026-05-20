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
    property bool isLoading: false

    signal projectSelected(string projectId)
    signal baselineSelected(string baselineId)
    signal refreshRequested()

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
            implicitHeight: toolbarRow.implicitHeight + (Theme.AppTheme.spacingSm * 2)

            RowLayout {
                id: toolbarRow
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                anchors.topMargin: Theme.AppTheme.spacingSm
                anchors.bottomMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingSm

                Label {
                    text: "Project"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                }

                ComboBox {
                    id: projectCombo

                    Layout.preferredWidth: Math.max(220, root.width * 0.34)
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
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                }

                ComboBox {
                    id: baselineCombo

                    Layout.preferredWidth: Math.max(190, root.width * 0.25)
                    enabled: !root.isLoading && !root.baselineSelectionLocked
                    model: root.baselineOptions || []
                    textRole: "label"
                    currentIndex: root.indexForValue(root.baselineOptions, root.selectedBaselineId)

                    onActivated: function(index) {
                        const option = root.baselineOptions[index]
                        root.baselineSelected(String(option && option.value ? option.value : ""))
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
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.baselineSelectionLocked
            text: root.baselineSelectionLocked
                ? "Portfolio mode summarizes the full portfolio and keeps baseline selection locked."
                : ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}
