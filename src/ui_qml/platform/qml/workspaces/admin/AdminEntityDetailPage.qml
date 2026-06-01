pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var entity: ({})
    property string fallbackTitle: "Entity"
    property string contextLabel: "Context"
    property string contextSubtitle: ""
    property string contextMessage: ""
    property string notesTitle: "Operational Notes"
    property string notesMessage: ""
    property string auditMessage: "Entity-level audit detail is routed through the shared Platform audit workspace."
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property var overviewFields: []
    property var contextFields: []
    property var overviewActions: []
    property var contextActions: []
    property var auditActions: []
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _state: (root.entity && root.entity.state) ? root.entity.state : ({})
    readonly property string _title: String(root.entity && root.entity.title ? root.entity.title : root.fallbackTitle)
    readonly property string _status: String(root.entity && root.entity.statusLabel ? root.entity.statusLabel : "")
    readonly property string _subtitle: String(root.entity && root.entity.subtitle ? root.entity.subtitle : "")
    readonly property string _supportingText: String(root.entity && root.entity.supportingText ? root.entity.supportingText : "")
    readonly property string _metaText: String(root.entity && root.entity.metaText ? root.entity.metaText : "")
    readonly property string _contextLabel: root.contextLabel.length > 0 ? root.contextLabel : "Context"
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": root._contextLabel },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        if (root._activeSectionLabel === "Overview") {
            return root._subtitle
        }
        if (root._activeSectionLabel === root._contextLabel) {
            if (root.contextSubtitle.length > 0) {
                return root.contextSubtitle
            }
            return root.contextMessage
        }
        return root.auditMessage
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return root.overviewActions || []
        }
        if (root._activeSectionLabel === root._contextLabel) {
            return root.contextActions || []
        }
        return root.auditActions || []
    }

    function _displayValue(value) {
        if (value === undefined || value === null) {
            return "-"
        }
        if (typeof value === "boolean") {
            return value ? "Yes" : "No"
        }
        const text = String(value)
        return text.length > 0 ? text : "-"
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        isBusy: root.busy
        showEdit: false
        showDelete: false
        sections: root._sections

        onBackRequested: root.backRequested()
        onSectionChanged: function(index) {
            root.activeSectionIndex = index
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                root.actionRequested(actionId)
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

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
                                    title: "Summary"
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
                                            model: root.overviewFields || []

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
                                                    text: root._displayValue(modelData.value)
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
                                    title: root.notesTitle
                                    outlined: true

                                    ColumnLayout {
                                        id: notesColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppWidgets.StatusChip {
                                            visible: root._status.length > 0
                                            status: root._status
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: root._supportingText.length > 0
                                            text: root._supportingText
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: root._metaText.length > 0
                                            text: root._metaText
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: root.notesMessage.length > 0
                                                ? root.notesMessage
                                                : "No additional operational notes are available for this record yet."
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
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 1 ? contextLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: contextLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading context..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: root._contextLabel
                        }

                        Item {
                            width: parent.width
                            implicitHeight: contextColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: contextColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    visible: root.contextMessage.length > 0
                                    tone: "info"
                                    message: root.contextMessage
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: contextFieldsColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: root._contextLabel
                                    outlined: true

                                    ColumnLayout {
                                        id: contextFieldsColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root.contextFields || []

                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    Layout.preferredWidth: 170
                                                    text: String(modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: root._displayValue(modelData.value)
                                                    color: Theme.AppTheme.textPrimary
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
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Audit"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: auditColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: auditColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: root.auditMessage
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: auditNotes.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Audit Follow-up"
                                    outlined: true

                                    ColumnLayout {
                                        id: auditNotes
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: "Use the shared audit workspace to inspect platform-wide events, approval history, and related operational activity for this record."
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
        }
    }
}
