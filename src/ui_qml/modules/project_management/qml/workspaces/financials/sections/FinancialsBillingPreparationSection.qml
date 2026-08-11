pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var profile: ({ "id": "", "statusLabel": "", "fields": [], "emptyState": "" })
    property var schedule: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var preparations: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    signal preparationPageRequested(int page)

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Billing Preparation"
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: "Ownership boundary"

            AppControls.Label {
                width: parent ? parent.width : 0
                text: "Project Finance prepares commercial billing evidence. Accounting remains authoritative for invoices, receivables, payments, tax, and ledger records."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: String(root.profile.id || "").length === 0
            title: "No billing profile"
            message: root.profile.emptyState || "Configure commercial terms before preparing billing evidence."
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            visible: String(root.profile.id || "").length > 0
            title: root.profile.statusLabel || "Commercial profile"

            GridLayout {
                width: parent ? parent.width : 0
                columns: width >= 720 ? 3 : (width >= 440 ? 2 : 1)
                columnSpacing: Theme.AppTheme.spacingLg
                rowSpacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: root.profile.fields || []
                    delegate: ColumnLayout {
                        id: fieldDelegate
                        required property var modelData
                        Layout.fillWidth: true
                        AppControls.Label {
                            text: String(fieldDelegate.modelData.label || "")
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(fieldDelegate.modelData.value || "-")
                            color: Theme.AppTheme.textPrimary
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }

        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.schedule
        }

        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.preparations
            onPageRequested: function(page) { root.preparationPageRequested(page) }
        }
    }
}
