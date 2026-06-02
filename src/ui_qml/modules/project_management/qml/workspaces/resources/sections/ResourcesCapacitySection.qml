pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var resourceDetail: ({ "id": "", "state": {} })

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0

    function _sv(key) {
        const s = root.resourceDetail.state || {}
        return String(s[key] || "")
    }

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Capacity" }

        Item {
            width: parent.width
            implicitHeight: _capacityCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _capacityCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasResource
                    title: "No capacity data"
                    message: "Select a resource to review its capacity settings."
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 52
                    visible: root._hasResource

                    Rectangle {
                        id: capacityCard
                        anchors.fill: parent
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt

                        readonly property real _pct: {
                            const s = root.resourceDetail.state || {}
                            return Math.min(parseFloat(s.capacityPercent || "0"), 100.0) / 100.0
                        }
                        readonly property string _label: {
                            const s = root.resourceDetail.state || {}
                            const pct = parseFloat(s.capacityPercent || "0")
                            return s.capacityLabel || (pct.toFixed(0) + "%")
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingXs

                            RowLayout {
                                Layout.fillWidth: true
                                AppControls.Label { text: "Capacity"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                Item { Layout.fillWidth: true }
                                AppControls.Label { text: capacityCard._label; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                            }

                            AppWidgets.ProgressBar {
                                Layout.fillWidth: true
                                value: capacityCard._pct
                                Layout.preferredHeight: 6
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    visible: root._hasResource && String((root.resourceDetail.state || {}).hourlyRateLabel || "").length > 0

                    Rectangle {
                        anchors.fill: parent
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingMd
                            anchors.rightMargin: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingSm
                            AppControls.Label { text: "Hourly Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                            Item { Layout.fillWidth: true }
                            AppControls.Label { text: root._sv("hourlyRateLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    visible: root._hasResource
                    Rectangle {
                        anchors.fill: parent
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingMd
                            anchors.rightMargin: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingSm
                            AppControls.Label { text: "Cost Type"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                            Item { Layout.fillWidth: true }
                            AppControls.Label { text: root._sv("costTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                        }
                    }
                }
            }
        }
    }
}
