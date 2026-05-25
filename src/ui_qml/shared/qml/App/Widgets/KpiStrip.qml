pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var metrics: []

    implicitHeight: Theme.AppTheme.normalRowHeight + Theme.AppTheme.sectionGap
    visible: root.metrics.length > 0

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.surfaceRaised
        radius: Theme.AppTheme.radiusMd

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            spacing: 0

            Repeater {
                model: root.metrics

                delegate: Item {
                    id: kpiCell
                    required property var modelData
                    required property int index

                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    readonly property color _trendColor: {
                        const t = kpiCell.modelData.trend || ""
                        if (t === "up")   return Theme.AppTheme.success
                        if (t === "down") return Theme.AppTheme.danger
                        return Theme.AppTheme.textMuted
                    }

                    readonly property string _trendArrow: {
                        const t = kpiCell.modelData.trend || ""
                        if (t === "up")   return "▲"
                        if (t === "down") return "▼"
                        return ""
                    }

                    // Separator between pills (not before first)
                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 10
                        anchors.bottomMargin: 10
                        width: 1
                        color: Theme.AppTheme.divider
                        visible: kpiCell.index > 0
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 1

                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                text: kpiCell.modelData.value || "—"
                                color: {
                                    const hint = kpiCell.modelData.colorHint || ""
                                    if (hint === "success") return Theme.AppTheme.success
                                    if (hint === "warning") return Theme.AppTheme.warning
                                    if (hint === "danger")  return Theme.AppTheme.danger
                                    return Theme.AppTheme.textPrimary
                                }
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }

                            Text {
                                visible: kpiCell._trendArrow !== ""
                                text: kpiCell._trendArrow
                                color: kpiCell._trendColor
                                font.pixelSize: Theme.AppTheme.iconXs
                            }

                            AppControls.Label {
                                visible: (kpiCell.modelData.trendLabel || "") !== "" && kpiCell._trendArrow !== ""
                                text: kpiCell.modelData.trendLabel || ""
                                color: kpiCell._trendColor
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                        }

                        AppControls.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: kpiCell.modelData.label || ""
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
