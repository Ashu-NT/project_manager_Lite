pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Item {
    id: root

    property string sectionLabel: ""
    property string infoMessage: ""
    property string cardTitle: "Operational Guidance"
    property var notes: []
    // -- Cross-module bridge card additions (Site's Projects/Documents
    // tabs): all optional and empty/zero by default, so Department's
    // existing text-only consumers (Projects/Users/Audit/Documents tabs)
    // render exactly as before when they don't pass these.
    property string icon: ""
    property string ctaLabel: ""
    property int maxContentWidth: 0

    signal ctaRequested()

    width: parent ? parent.width : 0
    implicitHeight: sectionColumn.implicitHeight

    Column {
        id: sectionColumn
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading {
            width: parent.width
            label: root.sectionLabel
        }

        Item {
            width: parent.width
            implicitHeight: contentColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: contentColumn
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                width: root.maxContentWidth > 0
                    ? Math.min(parent.width - Theme.AppTheme.spacingMd * 2, root.maxContentWidth)
                    : (parent.width - Theme.AppTheme.spacingMd * 2)
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.infoMessage.length > 0
                    tone: "info"
                    message: root.infoMessage
                }

                AppWidgets.SectionCard {

                    Layout.fillWidth: true
                    title: root.icon.length > 0 ? "" : root.cardTitle
                    outlined: true

                    ColumnLayout {
                        id: notesColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root.icon.length > 0
                            spacing: Theme.AppTheme.spacingSm

                            AppIcons.AppIcon {
                                visible: root.icon.length > 0
                                name: root.icon
                                iconColor: Theme.AppTheme.accent
                                size: Theme.AppTheme.iconMd
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: root.cardTitle
                                color: Theme.AppTheme.textPrimary
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }
                        }

                        Repeater {
                            model: root.notes || []

                            delegate: AppControls.Label {
                                required property var modelData
                                Layout.fillWidth: true
                                text: String(modelData || "")
                                color: Theme.AppTheme.textSecondary
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }

                        AppControls.SecondaryButton {
                            Layout.alignment: Qt.AlignRight
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            visible: root.ctaLabel.length > 0
                            text: root.ctaLabel
                            iconName: "chevron_right"
                            onClicked: root.ctaRequested()
                        }
                    }
                }
            }
        }
    }
}
