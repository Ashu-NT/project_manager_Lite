import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var baselinesModel: ({
        "options": [],
        "selectedBaselineAId": "",
        "selectedBaselineBId": "",
        "includeUnchanged": false,
        "summaryText": "",
        "rows": [],
        "emptyState": ""
    })
    property string selectedProjectId: ""
    property bool isBusy: false

    signal baselineASelected(string baselineId)
    signal baselineBSelected(string baselineId)
    signal includeUnchangedUpdated(bool includeUnchanged)
    signal createBaselineRequested(var payload)
    signal deleteBaselineRequested(string baselineId)

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function deleteTargetBaselineId() {
        return String(root.baselinesModel.selectedBaselineBId || root.baselinesModel.selectedBaselineAId || "")
    }

    implicitHeight: baselineColumn.implicitHeight

    ColumnLayout {
        id: baselineColumn

        width: parent ? parent.width : implicitWidth
        spacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.fillWidth: true
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
            implicitHeight: controlsColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

            ColumnLayout {
                id: controlsColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                Label {
                    Layout.fillWidth: true
                    text: "Baseline Management"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: "Create planning snapshots, compare drift between freezes, and remove stale baselines after review."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    TextField {
                        id: baselineNameField
                        Layout.fillWidth: true
                        placeholderText: "New baseline name"
                        enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
                    }

                    AppControls.PrimaryButton {
                        text: "Create Baseline"
                        enabled: !root.isBusy && String(root.selectedProjectId || "").length > 0
                        onClicked: root.createBaselineRequested({
                            "projectId": root.selectedProjectId,
                            "name": baselineNameField.text
                        })
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: width > 920 ? 4 : 2
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingSm

                    Label {
                        text: "From baseline"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: root.baselinesModel.options || []
                        textRole: "label"
                        enabled: !root.isBusy && (root.baselinesModel.options || []).length > 0
                        currentIndex: root.indexForValue(
                            root.baselinesModel.options || [],
                            root.baselinesModel.selectedBaselineAId || ""
                        )

                        onActivated: function(index) {
                            var option = (root.baselinesModel.options || [])[index]
                            if (option) {
                                root.baselineASelected(String(option.value || ""))
                            }
                        }
                    }

                    Label {
                        text: "To baseline"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: root.baselinesModel.options || []
                        textRole: "label"
                        enabled: !root.isBusy && (root.baselinesModel.options || []).length > 0
                        currentIndex: root.indexForValue(
                            root.baselinesModel.options || [],
                            root.baselinesModel.selectedBaselineBId || ""
                        )

                        onActivated: function(index) {
                            var option = (root.baselinesModel.options || [])[index]
                            if (option) {
                                root.baselineBSelected(String(option.value || ""))
                            }
                        }
                    }

                    CheckBox {
                        Layout.columnSpan: width > 920 ? 2 : 1
                        text: "Show unchanged tasks"
                        checked: Boolean(root.baselinesModel.includeUnchanged)
                        enabled: !root.isBusy && (root.baselinesModel.options || []).length > 1
                        onToggled: root.includeUnchangedUpdated(checked)
                    }

                    AppControls.PrimaryButton {
                        Layout.columnSpan: width > 920 ? 2 : 1
                        text: "Delete Selected Baseline"
                        danger: true
                        enabled: !root.isBusy && root.deleteTargetBaselineId().length > 0
                        onClicked: root.deleteBaselineRequested(root.deleteTargetBaselineId())
                    }
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(root.baselinesModel.summaryText || "").length > 0
                    text: String(root.baselinesModel.summaryText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: "Baseline Drift"
            subtitle: "Review start, finish, duration, and planning-cost deltas between two baseline freezes."
            emptyState: String(root.baselinesModel.emptyState || "")
            items: root.baselinesModel.rows || []
        }
    }
}
