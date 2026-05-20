import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property bool canExport: false
    property bool isBusy: false

    signal stockCsvRequested()
    signal stockExcelRequested()
    signal procurementCsvRequested()
    signal procurementExcelRequested()

    implicitHeight: contentLayout.implicitHeight

    ColumnLayout {
        id: contentLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Report Packages"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.titleSize
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: "Export the same stock-status and procurement-overview packages that the legacy reports tab generated, but now through the typed pricing controller."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: !root.canExport
            text: "Export permission is required to generate files from this workspace."
            color: "#8B1E1E"
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 980 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            Rectangle {
                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                implicitHeight: stockColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: stockColumn

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        Layout.fillWidth: true
                        text: "Stock Status"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "Site and storeroom filtered stock position package with summary metrics and detailed balance rows."
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            text: "Export CSV"
                            iconName: "export"
                            enabled: root.canExport && !root.isBusy
                            onClicked: root.stockCsvRequested()
                        }

                        AppControls.PrimaryButton {
                            text: "Export Excel"
                            iconName: "export"
                            enabled: root.canExport && !root.isBusy
                            onClicked: root.stockExcelRequested()
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                implicitHeight: procurementColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: procurementColumn

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        Layout.fillWidth: true
                        text: "Procurement Overview"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "Supplier-facing overview package for requisitions, purchase orders, receipts, and open quantity pressure."
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            text: "Export CSV"
                            iconName: "export"
                            enabled: root.canExport && !root.isBusy
                            onClicked: root.procurementCsvRequested()
                        }

                        AppControls.PrimaryButton {
                            text: "Export Excel"
                            iconName: "export"
                            enabled: root.canExport && !root.isBusy
                            onClicked: root.procurementExcelRequested()
                        }
                    }
                }
            }
        }
    }
}
