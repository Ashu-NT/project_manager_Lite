import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
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

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: selectionColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: selectionColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    text: "Project scope"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                ComboBox {
                    id: projectCombo

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
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    text: "Baseline"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                ComboBox {
                    id: baselineCombo

                    Layout.fillWidth: true
                    enabled: !root.isLoading && !root.baselineSelectionLocked
                    model: root.baselineOptions || []
                    textRole: "label"
                    currentIndex: root.indexForValue(root.baselineOptions, root.selectedBaselineId)

                    onActivated: function(index) {
                        const option = root.baselineOptions[index]
                        root.baselineSelected(String(option && option.value ? option.value : ""))
                    }
                }
            }

            AppControls.PrimaryButton {
                Layout.alignment: Qt.AlignBottom
                enabled: !root.isLoading
                text: "Refresh"
                onClicked: root.refreshRequested()
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.baselineSelectionLocked
                ? "Portfolio mode summarizes the full portfolio and keeps baseline selection locked."
                : "Switch project scope or baseline to inspect read-only schedule, resource, and delivery health."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }
    }
}
