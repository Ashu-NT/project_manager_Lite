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

        AppWidgets.SectionHeading { width: parent.width; label: "Cost Rates" }

        Item {
            width: parent.width
            implicitHeight: _costRatesCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _costRatesCol
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
                    title: "No cost rate data"
                    message: "Select a resource to review its cost rate configuration."
                }

                Item {
                    Layout.fillWidth: true
                    visible: root._hasResource
                    implicitHeight: _costRatesGrid.implicitHeight

                    GridLayout {
                        id: _costRatesGrid
                        width: parent.width
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingMd
                        rowSpacing: Theme.AppTheme.spacingXs

                        AppControls.Label { text: "Hourly Rate";  color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("hourlyRateLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                        AppControls.Label { text: "Currency";     color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("currency") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                        AppControls.Label { text: "Cost Type";    color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("costTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                        AppControls.Label { text: "Worker Type";  color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("workerTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                    }
                }
            }
        }
    }
}
