pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers

// Enterprise governance overview console.
// Left: Governance Activity timeline. Right: scrollable Runtime / Identity / Master Data panels.
ColumnLayout {
    id: root
    spacing: 0

    // ── Public API ────────────────────────────────────────────────
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController

    readonly property var _overview:  root.workspaceController ? (root.workspaceController.overview || {}) : ({})
    readonly property var _metrics:   root._overview.metrics   || []
    readonly property var _sections:  root._overview.sections  || []
    readonly property var _activity:  root._overview.activityFeed || []

    readonly property var _runtimeSection:   root._sections.length > 0
        ? root._sections[0] : { title: "Runtime Context",      rows: [], emptyState: "No runtime data" }
    readonly property var _workforceSection: root._sections.length > 1
        ? root._sections[1] : { title: "Identity & Workforce", rows: [], emptyState: "No identity data" }
    readonly property var _masterSection:    root._sections.length > 2
        ? root._sections[2] : { title: "Master Data Coverage", rows: [], emptyState: "No master data" }

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    property string _searchText: ""

    // ── Section title bar ─────────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
        color:  Theme.AppTheme.surfaceRaised
        z:      1

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        AppControls.Label {
            anchors.left:           parent.left
            anchors.leftMargin:     Theme.AppTheme.marginMd
            anchors.verticalCenter: parent.verticalCenter
            text:           "Audit & Overview"
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
        }
    }

    // ── TableToolbar ──────────────────────────────────────────────
    AppWidgets.TableToolbar {
        id: auditToolbar
        Layout.fillWidth:  true
        searchPlaceholder: "Search activity..."
        showFilter:        true
        showViews:         true
        showRefresh:       true
        isBusy:            root._busy
        onSearchChanged:    function(text) { root._searchText = text }
        onFilterClicked:    auditFilterPopup.open()
        onViewsClicked:     auditViewsPopup.open()
        onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
    }

    // ── Inline state banners ──────────────────────────────────────
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: (root._load || root._busy) && root._err.length === 0
        tone:    "info"
        message: root._busy ? "Saving changes..." : "Loading..."
    }
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root._err.length > 0
        tone:    "danger"
        message: root._err
    }
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root._ok.length > 0 && root._err.length === 0
        tone:    "success"
        message: root._ok
    }

    // ── KPI strip ─────────────────────────────────────────────────
    AppWidgets.KpiStrip {
        Layout.fillWidth: true
        metrics: root._metrics
    }

    // ── Main two-column area (fills remaining height) ─────────────
    RowLayout {
        Layout.fillWidth:  true
        Layout.fillHeight: true
        spacing: 0

        // ── Left: Governance Activity timeline ────────────────────
        ColumnLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 0

            AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Governance Activity" }

            Flickable {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                contentWidth:      width
                contentHeight:     _govFeed.implicitHeight + Theme.AppTheme.marginMd * 2
                clip:              true
                boundsBehavior:    Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                AppWidgets.ActivityFeed {
                    id: _govFeed
                    anchors {
                        top:         parent.top
                        left:        parent.left
                        right:       parent.right
                        topMargin:   4
                        leftMargin:  Theme.AppTheme.marginSm
                        rightMargin: Theme.AppTheme.marginSm
                    }
                    items:     root._activity
                    emptyText: "No governance activity recorded"
                }
            }
        }

        // Column divider
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 1; color: Theme.AppTheme.divider
        }

        // ── Right: Runtime + Identity + Master Data (scrollable) ──
        Flickable {
            Layout.preferredWidth: 300
            Layout.fillHeight:     true
            contentWidth:          width
            contentHeight:         _rightContent.implicitHeight
            clip:                  true
            boundsBehavior:        Flickable.StopAtBounds

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: _rightContent
                anchors { left: parent.left; right: parent.right; top: parent.top }
                spacing: 0

                // ── Runtime Context ───────────────────────────────
                AppWidgets.SectionHeading {
                    Layout.fillWidth: true
                    label: root._runtimeSection.title || "Runtime Context"
                }

                ColumnLayout {
                    Layout.fillWidth:    true
                    Layout.leftMargin:   Theme.AppTheme.marginMd
                    Layout.rightMargin:  Theme.AppTheme.marginMd
                    Layout.topMargin:    Theme.AppTheme.spacingXs
                    Layout.bottomMargin: Theme.AppTheme.spacingMd
                    spacing:             Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._runtimeSection.rows || []

                        delegate: ColumnLayout {
                            id: _rtRow
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.Label {
                                    text:           _rtRow.modelData.label || ""
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                    Layout.preferredWidth: 130
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text:           _rtRow.modelData.value || "-"
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      true
                                    elide:          Text.ElideRight
                                }
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible:        String(_rtRow.modelData.supportingText || "").length > 0
                                text:           _rtRow.modelData.supportingText || ""
                                color:          Theme.AppTheme.textSecondary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode:       Text.WordWrap
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1; color: Theme.AppTheme.divider
                                visible: _rtRow.index < (root._runtimeSection.rows || []).length - 1
                            }
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: (root._runtimeSection.rows || []).length === 0
                        text:    root._runtimeSection.emptyState || "No runtime data"
                        color:   Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

                // ── Identity & Workforce ──────────────────────────
                AppWidgets.SectionHeading {
                    Layout.fillWidth: true
                    label: root._workforceSection.title || "Identity & Workforce"
                }

                ColumnLayout {
                    Layout.fillWidth:    true
                    Layout.leftMargin:   Theme.AppTheme.marginMd
                    Layout.rightMargin:  Theme.AppTheme.marginMd
                    Layout.topMargin:    Theme.AppTheme.spacingXs
                    Layout.bottomMargin: Theme.AppTheme.spacingMd
                    spacing:             Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._workforceSection.rows || []

                        delegate: ColumnLayout {
                            id: _wfRow
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.Label {
                                    text:           _wfRow.modelData.label || ""
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                    Layout.preferredWidth: 130
                                }

                                AppControls.Label {
                                    text:           _wfRow.modelData.value || "-"
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      true
                                }
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible:        String(_wfRow.modelData.supportingText || "").length > 0
                                text:           _wfRow.modelData.supportingText || ""
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide:          Text.ElideRight
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1; color: Theme.AppTheme.divider
                                visible: _wfRow.index < (root._workforceSection.rows || []).length - 1
                            }
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: (root._workforceSection.rows || []).length === 0
                        text:    root._workforceSection.emptyState || "No identity data"
                        color:   Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

                // ── Master Data Coverage ──────────────────────────
                AppWidgets.SectionHeading {
                    Layout.fillWidth: true
                    label: root._masterSection.title || "Master Data Coverage"
                }

                ColumnLayout {
                    Layout.fillWidth:    true
                    Layout.leftMargin:   Theme.AppTheme.marginMd
                    Layout.rightMargin:  Theme.AppTheme.marginMd
                    Layout.topMargin:    Theme.AppTheme.spacingXs
                    Layout.bottomMargin: Theme.AppTheme.spacingMd
                    spacing:             Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._masterSection.rows || []

                        delegate: ColumnLayout {
                            id: _mdRow
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.Label {
                                    text:           _mdRow.modelData.label || ""
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                    Layout.preferredWidth: 130
                                }

                                AppControls.Label {
                                    text:           _mdRow.modelData.value || "-"
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      true
                                }
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible:        String(_mdRow.modelData.supportingText || "").length > 0
                                text:           _mdRow.modelData.supportingText || ""
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1; color: Theme.AppTheme.divider
                                visible: _mdRow.index < (root._masterSection.rows || []).length - 1
                            }
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: (root._masterSection.rows || []).length === 0
                        text:    root._masterSection.emptyState || "No master data"
                        color:   Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }
                }
            }
        }
    }

    // ── Filter popup ──────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: auditFilterPopup
        anchorItem: auditToolbar.filterButtonItem
        implicitWidth: 280
        padding:     Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color:        Theme.AppTheme.surfaceRaised
            radius:       Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        ColumnLayout {
            width: parent.width; spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                text:           "Filter Governance"
                color:          Theme.AppTheme.textPrimary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold:      true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text:    "Event type and date filters will appear here."
                color:   Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.SecondaryButton {
                Layout.alignment: Qt.AlignRight
                text: "Close"; onClicked: auditFilterPopup.close()
            }
        }
    }

    // ── Views popup ───────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: auditViewsPopup
        anchorItem: auditToolbar.viewsButtonItem
        implicitWidth: 240
        padding:     4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color:        Theme.AppTheme.surfaceRaised
            radius:       Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        Column {
            width: parent.width; spacing: 2

            Repeater {
                model: [
                    "All Events",
                    "Access Changes",
                    "Module Events",
                    "Site & Org Changes",
                    "Configuration Changes"
                ]

                delegate: Rectangle {
                    id: delegateRow
                    required property string modelData
                    required property int    index
                    width: parent.width; height: 34
                    radius: Theme.AppTheme.radiusMd
                    color:  _avMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                    AppControls.Label {
                        anchors {
                            left:           parent.left
                            leftMargin:     Theme.AppTheme.spacingMd
                            verticalCenter: parent.verticalCenter
                        }
                        text:           delegateRow.modelData
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }

                    MouseArea {
                        id: _avMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape:  Qt.PointingHandCursor
                        onClicked:    auditViewsPopup.close()
                    }
                }
            }
        }
    }
}
