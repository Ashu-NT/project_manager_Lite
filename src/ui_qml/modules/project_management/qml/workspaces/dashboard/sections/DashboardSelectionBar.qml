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

    function optionValue(options, index) {
        const rows = options || []
        if (index < 0 || index >= rows.length) {
            return ""
        }
        return String(rows[index].value || "")
    }

    function indexForValue(options, selectedValue) {
        const rows = options || []
        for (let index = 0; index < rows.length; index += 1) {
            if (String(rows[index].value || "") === String(selectedValue || "")) {
                return index
            }
        }
        return rows.length > 0 ? 0 : -1
    }

    function syncComboSelection(combo, options, selectedValue) {
        if (!combo) {
            return
        }
        const nextIndex = root.indexForValue(options, selectedValue)
        if (combo.currentIndex === nextIndex) {
            return
        }
        combo.syncingSelection = true
        combo.currentIndex = nextIndex
        Qt.callLater(function() {
            combo.syncingSelection = false
        })
    }

    function syncProjectCombo() {
        root.syncComboSelection(projectCombo, root.projectOptions, root.selectedProjectId)
    }

    function syncBaselineCombo() {
        root.syncComboSelection(baselineCombo, root.baselineOptions, root.selectedBaselineId)
    }

    function syncPeriodCombo() {
        root.syncComboSelection(periodCombo, root.periodOptions, root.selectedPeriodKey)
    }

    function syncViewCombo() {
        root.syncComboSelection(viewCombo, root.viewOptions, root.selectedViewKey)
    }

    readonly property bool baselineSelectionLocked: (root.baselineOptions || []).length === 1
        && String(root.baselineOptions[0].label || "") === "Portfolio view"

    implicitHeight: toolbarColumn.implicitHeight
    Component.onCompleted: {
        root.syncProjectCombo()
        root.syncBaselineCombo()
        root.syncPeriodCombo()
        root.syncViewCombo()
    }
    onProjectOptionsChanged: Qt.callLater(root.syncProjectCombo)
    onSelectedProjectIdChanged: Qt.callLater(root.syncProjectCombo)
    onBaselineOptionsChanged: Qt.callLater(root.syncBaselineCombo)
    onSelectedBaselineIdChanged: Qt.callLater(root.syncBaselineCombo)
    onPeriodOptionsChanged: Qt.callLater(root.syncPeriodCombo)
    onSelectedPeriodKeyChanged: Qt.callLater(root.syncPeriodCombo)
    onViewOptionsChanged: Qt.callLater(root.syncViewCombo)
    onSelectedViewKeyChanged: Qt.callLater(root.syncViewCombo)

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

                AppControls.Label {
                    text: "Scope"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.ComboBox {
                    id: projectCombo

                    property bool syncingSelection: false

                    Layout.preferredWidth: Math.max(220, root.width * 0.24)
                    Layout.fillWidth: true
                    enabled: !root.isLoading
                    model: root.projectOptions || []
                    textRole: "label"

                    onActivated: function(index) {
                        if (projectCombo.syncingSelection) {
                            return
                        }
                        const nextValue = root.optionValue(root.projectOptions, index)
                        if (nextValue !== String(root.selectedProjectId || "")) {
                            root.projectSelected(nextValue)
                        }
                    }
                }

                AppControls.Label {
                    text: "Baseline"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.ComboBox {
                    id: baselineCombo

                    property bool syncingSelection: false

                    Layout.preferredWidth: 210
                    enabled: !root.isLoading && !root.baselineSelectionLocked
                    model: root.baselineOptions || []
                    textRole: "label"

                    onActivated: function(index) {
                        if (baselineCombo.syncingSelection) {
                            return
                        }
                        const nextValue = root.optionValue(root.baselineOptions, index)
                        if (nextValue !== String(root.selectedBaselineId || "")) {
                            root.baselineSelected(nextValue)
                        }
                    }
                }

                AppControls.Label {
                    text: "Period"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.ComboBox {
                    id: periodCombo

                    property bool syncingSelection: false

                    Layout.preferredWidth: 150
                    enabled: !root.isLoading
                    model: root.periodOptions || []
                    textRole: "label"

                    onActivated: function(index) {
                        if (periodCombo.syncingSelection) {
                            return
                        }
                        const nextValue = root.optionValue(root.periodOptions, index)
                        if (nextValue !== String(root.selectedPeriodKey || "")) {
                            root.periodSelected(nextValue)
                        }
                    }
                }

                AppControls.Label {
                    text: "View"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.ComboBox {
                    id: viewCombo

                    property bool syncingSelection: false

                    Layout.preferredWidth: 190
                    enabled: !root.isLoading
                    model: root.viewOptions || []
                    textRole: "label"

                    onActivated: function(index) {
                        if (viewCombo.syncingSelection) {
                            return
                        }
                        const nextValue = root.optionValue(root.viewOptions, index)
                        if (nextValue !== String(root.selectedViewKey || "")) {
                            root.viewSelected(nextValue)
                        }
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

        AppControls.Label {
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

