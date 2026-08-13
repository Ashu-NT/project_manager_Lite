pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
            color: Theme.AppTheme.surfaceRaised
            z: 1
            Rectangle {
                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                height: 1; color: Theme.AppTheme.divider
            }
            AppControls.Label {
                anchors.left: parent.left
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.verticalCenter: parent.verticalCenter
                text: "Platform Defaults"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: _defaultsContent.implicitHeight + Theme.AppTheme.marginLg * 2
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: _defaultsContent
                anchors {
                    top: parent.top; left: parent.left; right: parent.right
                    topMargin: Theme.AppTheme.marginLg; leftMargin: Theme.AppTheme.marginLg; rightMargin: Theme.AppTheme.marginLg
                }
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: [
                        { title: "Locale & Fiscal", rows: [
                            { label: "Default timezone",      value: "UTC+00:00 (configurable per org)" },
                            { label: "Base currency",         value: "USD — US Dollar" },
                            { label: "Date format",           value: "YYYY-MM-DD (ISO 8601)" },
                            { label: "Fiscal year start",     value: "January 1" },
                            { label: "Number format",         value: "1,234.56 (comma thousands)" }
                        ]},
                        { title: "Data Management", rows: [
                            { label: "Audit log retention",   value: "7 years (regulatory default)" },
                            { label: "Soft-delete retention", value: "90 days before hard purge" },
                            { label: "Document storage",      value: "Local filesystem (configurable)" },
                            { label: "Export format",         value: "CSV, XLSX, JSON" },
                            { label: "Max import batch",      value: "5,000 records" }
                        ]},
                        { title: "Approval Workflow", rows: [
                            { label: "Default SLA",           value: "48 hours (business days)" },
                            { label: "Reminder cadence",      value: "24 h before expiry" },
                            { label: "Auto-expire",           value: "Enabled — rejects after 7 days" },
                            { label: "Delegation allowed",    value: "Yes — to same-role users" },
                            { label: "Multi-level approval",  value: "Disabled (single approver)" }
                        ]},
                        { title: "Notification Defaults", rows: [
                            { label: "Email notifications",   value: "Enabled for all approval events" },
                            { label: "In-app notifications",  value: "Enabled" },
                            { label: "Digest frequency",      value: "Daily (08:00 local time)" },
                            { label: "Escalation alerts",     value: "Enabled — admin + manager" }
                        ]},
                        { title: "Compliance & Governance", rows: [
                            { label: "Immutable audit trail", value: "Enabled — all state changes logged" },
                            { label: "Data sovereignty",      value: "Org-scoped — no cross-tenant reads" },
                            { label: "PII masking",           value: "Enabled in exports" },
                            { label: "Change justification",  value: "Required for module lifecycle" },
                            { label: "Regulatory framework",  value: "ISO 27001 aligned" }
                        ]}
                    ]

                    delegate: Rectangle {
                        id: _defaultCard
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: _defaultCardLayout.implicitHeight + Theme.AppTheme.marginMd * 2
                        color: Theme.AppTheme.surface
                        radius: Theme.AppTheme.radiusMd
                        border.color: Theme.AppTheme.divider
                        border.width: 1

                        ColumnLayout {
                            id: _defaultCardLayout
                            anchors { fill: parent; margins: Theme.AppTheme.marginMd }
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: _defaultCard.modelData.title
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }

                            Repeater {
                                model: _defaultCard.modelData.rows || []
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm
                                    AppControls.Label { Layout.preferredWidth: 190; text: modelData.label; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                                    AppControls.Label { Layout.fillWidth: true; text: modelData.value; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; wrapMode: Text.WrapAtWordBoundaryOrAnywhere }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
