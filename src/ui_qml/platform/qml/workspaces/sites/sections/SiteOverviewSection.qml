pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Site Detail's Overview tab -- a presentational section only; all data is
// supplied by the orchestrator (AdminSiteDetailPage.qml).
Column {
    id: root
    width: parent ? parent.width : 0
    spacing: 0

    property var overviewFields: []
    property string status: ""
    property string statusTone: "neutral"
    property string supportingText: ""
    property string metaText: ""
    property string description: ""

    AppWidgets.SectionHeading {
        width: parent.width
        label: "Overview"
    }

    Item {
        width: parent.width
        implicitHeight: overviewColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

        ColumnLayout {
            id: overviewColumn
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: Theme.AppTheme.spacingMd
            anchors.leftMargin: Theme.AppTheme.spacingMd
            anchors.rightMargin: Theme.AppTheme.spacingMd
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                title: "Site Summary"
                outlined: true

                GridLayout {
                    id: overviewGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    columns: 2
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root.overviewFields

                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: modelData.value === undefined || modelData.value === null || String(modelData.value).length === 0
                                    ? "-"
                                    : (typeof modelData.value === "boolean" ? (modelData.value ? "Yes" : "No") : String(modelData.value))
                                color: Theme.AppTheme.textPrimary
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }
                    }
                }
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                implicitHeight: notesColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                title: "Operational Notes"
                outlined: true

                ColumnLayout {
                    id: notesColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.StatusChip {
                        visible: root.status.length > 0
                        status: root.status
                        tone: root.statusTone
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: root.supportingText.length > 0
                        text: root.supportingText
                        color: Theme.AppTheme.textSecondary
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: root.metaText.length > 0
                        text: root.metaText
                        color: Theme.AppTheme.textMuted
                        font.pixelSize: Theme.AppTheme.captionSize
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.description
                        color: Theme.AppTheme.textSecondary
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }
                }
            }
        }
    }
}
