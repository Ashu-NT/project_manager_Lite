pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var resourceDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "Select a resource from the pool to review details or edit its setup.",
        "fields": [], "state": {}
    })

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

        AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

        Item {
            width: parent.width
            implicitHeight: _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _overviewCol
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
                    title: "No resource selected"
                    message: root.resourceDetail.emptyState
                        || "Select a resource from the pool to review details or edit its setup."
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._hasResource
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Role"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("role") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Type"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("workerTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Capacity"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: {
                                const pct = parseFloat(root._sv("capacityPercent") || "0")
                                return root._sv("capacityLabel") || (pct.toFixed(0) + "%")
                            }
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("hourlyRateLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    visible: root._hasResource
                    color: Theme.AppTheme.divider
                    opacity: 0.5
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._hasResource
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Contact"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("contact") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Currency"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("currency") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Status"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppWidgets.StatusChip { status: root.resourceDetail.statusLabel || "" }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label { text: "Version"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root._sv("version") ? "v" + root._sv("version") : "-"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: root._hasResource
                    text: root.resourceDetail.description || "No additional details have been added for this resource."
                    color: String(root.resourceDetail.description || "").length > 0
                        ? Theme.AppTheme.textSecondary
                        : Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                    maximumLineCount: 4
                    elide: Text.ElideRight
                }
            }
        }
    }
}
