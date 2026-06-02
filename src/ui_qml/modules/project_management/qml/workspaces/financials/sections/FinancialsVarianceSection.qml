pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var baselineVarianceModel: []

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Variance" }

        AppWidgets.EmptyState {
            width: parent.width
            visible: (root.baselineVarianceModel || []).length === 0
            title: "No variance data"
            message: "Approve a baseline to see cost drift against the plan."
        }

        Item {
            width: parent.width
            visible: (root.baselineVarianceModel || []).length > 0
            implicitHeight: _varianceTable.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            Column {
                id: _varianceTable
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: 2

                Repeater {
                    model: root.baselineVarianceModel || []

                    delegate: Rectangle {
                        id: _varRow
                        required property var modelData
                        required property int index
                        width: _varianceTable.width
                        implicitHeight: _varRowContent.implicitHeight + Theme.AppTheme.spacingSm * 2
                        color: _varRow.index % 2 === 0 ? Theme.AppTheme.surfaceAlt : "transparent"
                        radius: Theme.AppTheme.radiusSm

                        readonly property color _toneColor: {
                            const t = String(_varRow.modelData.tone || "")
                            if (t === "danger")  return Theme.AppTheme.danger
                            if (t === "success") return Theme.AppTheme.success
                            return Theme.AppTheme.textPrimary
                        }

                        RowLayout {
                            id: _varRowContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.spacingSm
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_varRow.modelData.taskName || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide: Text.ElideRight
                            }
                            AppControls.Label {
                                text: {
                                    const sv = _varRow.modelData.startVarianceDays || 0
                                    const fv = _varRow.modelData.finishVarianceDays || 0
                                    if (sv === 0 && fv === 0) return "On schedule"
                                    const parts = []
                                    if (sv !== 0) parts.push("Start " + (sv > 0 ? "+" : "") + sv + "d")
                                    if (fv !== 0) parts.push("Finish " + (fv > 0 ? "+" : "") + fv + "d")
                                    return parts.join(" / ")
                                }
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                text: String(_varRow.modelData.costVarianceLabel || "—")
                                color: _varRow._toneColor
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }
                }
            }
        }
    }
}
