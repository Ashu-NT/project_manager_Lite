pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var forecastModel: ({
        "method": "", "methodLabel": "", "bacLabel": "", "acLabel": "", "evLabel": "",
        "etcLabel": "", "eacLabel": "", "vacLabel": "", "cpiLabel": "",
        "isOverBudget": false, "exceedsThreshold": false, "alertMessage": "", "metrics": []
    })
    property bool isBusy: false

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Forecast" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.forecastModel.alertMessage || "").length > 0
            tone: root.forecastModel.exceedsThreshold ? "danger" : "warning"
            message: root.forecastModel.alertMessage || ""
        }

        Item {
            width: parent.width
            implicitHeight: _fcastContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _fcastContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(root.forecastModel.methodLabel || "").length > 0
                    text: "Method: " + String(root.forecastModel.methodLabel || "")
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 4
                    columnSpacing: Theme.AppTheme.spacingSm
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root.forecastModel.metrics || []

                        delegate: Rectangle {
                            id: _fcastCell
                            required property var modelData
                            Layout.fillWidth: true
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surfaceAlt
                            implicitHeight: _fcastCellContent.implicitHeight + Theme.AppTheme.spacingSm * 2

                            readonly property color _valueColor: {
                                const hint = String(_fcastCell.modelData.colorHint || "")
                                if (hint === "success") return Theme.AppTheme.success
                                if (hint === "warning") return Theme.AppTheme.warning
                                if (hint === "danger")  return Theme.AppTheme.danger
                                return Theme.AppTheme.textPrimary
                            }

                            ColumnLayout {
                                id: _fcastCellContent
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.AppTheme.spacingSm
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_fcastCell.modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(_fcastCell.modelData.value || "-")
                                    color: _fcastCell._valueColor
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                    wrapMode: Text.NoWrap
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: (root.forecastModel.metrics || []).length === 0
                    text: "Select a project to view EAC/ETC forecast metrics."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
