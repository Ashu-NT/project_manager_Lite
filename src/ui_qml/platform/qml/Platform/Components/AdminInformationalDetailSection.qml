pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string sectionLabel: ""
    property string infoMessage: ""
    property string cardTitle: "Operational Guidance"
    property var notes: []

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
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.infoMessage.length > 0
                    tone: "info"
                    message: root.infoMessage
                }

                AppWidgets.SectionCard {
                    // No explicit implicitHeight override -- SectionCard
                    // already computes its own content-area height from its
                    // child's childrenRect (see SectionCard.qml) precisely
                    // so anchored content is never clipped. Overriding it
                    // here with notesColumn.implicitHeight + spacingMd*2
                    // omitted SectionCard's own title-bar height, silently
                    // clipping the last note whenever there was more than
                    // one (confirmed via visual QA on Site's Documents/
                    // Projects bridge cards, both consumers of this shared
                    // component).
                    Layout.fillWidth: true
                    title: root.cardTitle
                    outlined: true

                    ColumnLayout {
                        id: notesColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

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
                    }
                }
            }
        }
    }
}
