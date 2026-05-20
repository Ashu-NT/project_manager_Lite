import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectOptions: []
    property string selectedProjectId: ""
    property bool isBusy: false

    signal projectSelected(string projectId)
    signal refreshRequested()
    signal recalculateRequested()

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    implicitHeight: controlsLayout.implicitHeight

    RowLayout {
        id: controlsLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        ComboBox {
            Layout.preferredWidth: 260
            model: root.projectOptions
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root.indexForValue(root.projectOptions, root.selectedProjectId)

            onActivated: function(index) {
                var option = root.projectOptions[index]
                if (option) {
                    root.projectSelected(String(option.value || ""))
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: "Recalculate the selected project schedule, then review baseline drift and the current critical path."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Button {
            text: "Refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }

        AppControls.PrimaryButton {
            text: "Recalculate"
            iconName: "refresh"
            enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
            onClicked: root.recalculateRequested()
        }
    }
}
