pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var forecastModel: ({
        "exceedsThreshold": false, "alertMessage": "", "metrics": []
    })
    property bool isBusy: false

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Earned Value" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.forecastModel.alertMessage || "").length > 0
            tone: root.forecastModel.exceedsThreshold ? "danger" : "warning"
            message: root.forecastModel.alertMessage || ""
        }

        AppWidgets.EmptyState {
            width: parent.width
            visible: (root.forecastModel.metrics || []).length === 0
            title: "No EV data"
            message: "Select a project to view earned value metrics (BAC, AC, EV, ETC, EAC, VAC, CPI)."
        }

        Item {
            width: parent.width
            visible: (root.forecastModel.metrics || []).length > 0
            implicitHeight: _evGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            GridLayout {
                id: _evGrid
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                columns: 4
                columnSpacing: Theme.AppTheme.spacingSm
                rowSpacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: root.forecastModel.metrics || []

                    delegate: Rectangle {
                        id: _evCard
                        required property var modelData
                        Layout.fillWidth: true
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        implicitHeight: _evCardContent.implicitHeight + Theme.AppTheme.spacingSm * 2

                        readonly property color _valueColor: {
                            const hint = String(_evCard.modelData.colorHint || "")
                            if (hint === "success") return Theme.AppTheme.success
                            if (hint === "warning") return Theme.AppTheme.warning
                            if (hint === "danger")  return Theme.AppTheme.danger
                            return Theme.AppTheme.textPrimary
                        }

                        ColumnLayout {
                            id: _evCardContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.spacingSm
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_evCard.modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_evCard.modelData.value || "-")
                                color: _evCard._valueColor
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
        }
    }
}
