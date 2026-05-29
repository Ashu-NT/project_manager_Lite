import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers

ColumnLayout {
    id: root
    spacing: 0

    property PlatformControllers.PlatformAdminAccessWorkspaceController controller: null

    property string _selectedGrantId:   ""
    property string _selectedSessionId: ""

    readonly property var _selectedGrantItem: {
        const id = root._selectedGrantId
        if (!id) return null
        const items = root.controller ? (root.controller.scopeGrants.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _selectedSessionItem: {
        const id = root._selectedSessionId
        if (!id) return null
        const items = root.controller ? (root.controller.securityUsers.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property var _sessionActions: {
        const item = root._selectedSessionItem
        if (!item) return []
        const acts = []
        if (item.canPrimaryAction)
            acts.push({ id: "unlock", label: "Unlock Account",  icon: "approve", enabled: true, danger: false })
        if (item.canSecondaryAction)
            acts.push({ id: "revoke", label: "Revoke Sessions", icon: "delete",  enabled: true, danger: true  })
        return acts
    }

    readonly property var _grantsColumns: [
        { key: "title",       label: "Principal", flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Username",  flex: 2, minWidth: 110, sortable: false, visible: true },
        { key: "statusLabel", label: "Role",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Assigned",  flex: 2, minWidth: 130, sortable: false, visible: true }
    ]

    readonly property var _sessionsColumns: [
        { key: "title",          label: "User",     flex: 2, minWidth: 120, sortable: true,  visible: true },
        { key: "subtitle",       label: "Username", flex: 2, minWidth: 100, sortable: false, visible: true },
        { key: "statusLabel",    label: "Status",   flex: 0, minWidth: 80,  sortable: false, visible: true, type: "status" },
        { key: "supportingText", label: "Posture",  flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "metaText",       label: "Details",  flex: 3, minWidth: 200, sortable: false, visible: true }
    ]

    function indexOfOption(options, value) {
        for (let i = 0; i < options.length; i++) {
            if ((options[i].value || "") === value) return i
        }
        return options.length > 0 ? 0 : -1
    }

    function optionValue(options, index) {
        if (index < 0 || index >= options.length) return ""
        return options[index].value || ""
    }

    // ── Section title bar ─────────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        height: Theme.AppTheme.toolbarHeight - 6
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
            text:           "Roles & Access"
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
        }
    }

    // ── Table toolbar ─────────────────────────────────────────────
    AppWidgets.TableToolbar {
        Layout.fillWidth: true
        showRefresh: true
        isBusy:      root.controller ? root.controller.isBusy : false
        onRefreshRequested: { if (root.controller) root.controller.refresh() }
    }

    // ── Inline state banners ──────────────────────────────────────
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.controller
            ? ((root.controller.isLoading || root.controller.isBusy) && root.controller.errorMessage.length === 0)
            : false
        tone:    "info"
        message: root.controller ? (root.controller.isBusy ? "Saving..." : "Loading...") : ""
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.controller ? root.controller.errorMessage.length > 0 : false
        tone:    "danger"
        message: root.controller ? root.controller.errorMessage : ""
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.controller
            ? (root.controller.feedbackMessage.length > 0 && root.controller.errorMessage.length === 0)
            : false
        tone:    "success"
        message: root.controller ? root.controller.feedbackMessage : ""
    }

    // ── Access assignment panel ───────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: _assignPanel.implicitHeight + Theme.AppTheme.spacingSm * 2
        color: Theme.AppTheme.surfaceOverlay

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        ColumnLayout {
            id: _assignPanel
            anchors {
                left:        parent.left
                right:       parent.right
                top:         parent.top
                leftMargin:  Theme.AppTheme.marginMd
                rightMargin: Theme.AppTheme.marginMd
                topMargin:   Theme.AppTheme.spacingSm
            }
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text:               "ACCESS ASSIGNMENT"
                color:              Theme.AppTheme.textMuted
                font.family:        Theme.AppTheme.fontFamily
                font.pixelSize:     Theme.AppTheme.captionSize
                font.bold:          true
                font.letterSpacing: 0.8
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    AppControls.Label {
                        text:           "Scope Type"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }

                    AppControls.ComboBox {
                        id: _scopeTypeCombo
                        Layout.fillWidth: true
                        enabled:      root.controller ? !root.controller.isBusy : false
                        model:        root.controller ? root.controller.scopeTypeOptions : []
                        textRole:     "label"
                        currentIndex: root.indexOfOption(
                            root.controller ? root.controller.scopeTypeOptions : [],
                            root.controller ? root.controller.selectedScopeType : ""
                        )
                        onActivated: {
                            if (root.controller)
                                root.controller.setScopeType(root.optionValue(root.controller.scopeTypeOptions, currentIndex))
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    AppControls.Label {
                        text:           "Scope"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }

                    AppControls.ComboBox {
                        id: _scopeCombo
                        Layout.fillWidth: true
                        enabled:      root.controller ? !root.controller.isBusy : false
                        model:        root.controller ? root.controller.scopeOptions : []
                        textRole:     "label"
                        currentIndex: root.indexOfOption(
                            root.controller ? root.controller.scopeOptions : [],
                            root.controller ? root.controller.selectedScopeId : ""
                        )
                        onActivated: {
                            if (root.controller)
                                root.controller.setScopeId(root.optionValue(root.controller.scopeOptions, currentIndex))
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    AppControls.Label {
                        text:           "Principal"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }

                    AppControls.ComboBox {
                        id: _userCombo
                        Layout.fillWidth: true
                        enabled:      root.controller ? !root.controller.isBusy : false
                        model:        root.controller ? root.controller.userOptions : []
                        textRole:     "label"
                        currentIndex: root.indexOfOption(
                            root.controller ? root.controller.userOptions : [],
                            root.controller ? root.controller.selectedUserId : ""
                        )
                        onActivated: {
                            if (root.controller)
                                root.controller.setSelectedUserId(root.optionValue(root.controller.userOptions, currentIndex))
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    AppControls.Label {
                        text:           "Role"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }

                    AppControls.ComboBox {
                        id: _roleCombo
                        Layout.fillWidth: true
                        enabled:      root.controller ? !root.controller.isBusy : false
                        model:        root.controller ? root.controller.roleOptions : []
                        textRole:     "label"
                        currentIndex: root.indexOfOption(
                            root.controller ? root.controller.roleOptions : [],
                            root.controller ? root.controller.selectedRole : ""
                        )
                        onActivated: {
                            if (root.controller)
                                root.controller.setSelectedRole(root.optionValue(root.controller.roleOptions, currentIndex))
                        }
                    }
                }

                AppControls.PrimaryButton {
                    Layout.alignment: Qt.AlignBottom
                    text:     "Assign Access"
                    iconName: "approve"
                    enabled:  root.controller ? !root.controller.isBusy : false
                    onClicked: { if (root.controller) root.controller.assignMembership() }
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible:        text.length > 0
                text:           root.controller ? root.controller.scopeHint : ""
                color:          Theme.AppTheme.textSecondary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode:       Text.WordWrap
            }
        }
    }

    // ── Scoped Access Grants ──────────────────────────────────────
    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Scoped Access Grants" }

    RowLayout {
        Layout.fillWidth:  true
        Layout.fillHeight: true
        Layout.minimumHeight: 100
        spacing: 0

        AppWidgets.DataTable {
            id: _grantsTable
            Layout.fillWidth:  true
            Layout.fillHeight: true
            sourceModel:   root.controller ? root.controller.scopeGrantsTableModel : null
            columns:       root._grantsColumns
            emptyText:     root.controller ? (root.controller.scopeGrants.emptyState || "No access grants") : "No access grants"
            selectedRowId: root._selectedGrantId
            onRowSelected:  function(rowId) { root._selectedGrantId = rowId }
            onRowActivated: function(rowId) { root._selectedGrantId = rowId }
        }

        // Grant inspector
        Rectangle {
            Layout.fillHeight:    true
            Layout.preferredWidth: 272
            visible: root._selectedGrantItem !== null
            color:   Theme.AppTheme.surface
            z:       1

            Rectangle {
                anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                width: 1; color: Theme.AppTheme.divider
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Inspector header
                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.AppTheme.toolbarHeight - 6
                    color:  Theme.AppTheme.surfaceRaised

                    Rectangle {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }

                    AppControls.Label {
                        anchors.left:           parent.left
                        anchors.leftMargin:     Theme.AppTheme.marginMd
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right:          _grantCloseBtn.left
                        anchors.rightMargin:    4
                        text:           "Grant Details"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold:      true
                        elide:          Text.ElideRight
                    }

                    Rectangle {
                        id: _grantCloseBtn
                        anchors.right:          parent.right
                        anchors.rightMargin:    6
                        anchors.verticalCenter: parent.verticalCenter
                        width: 26; height: 26; radius: 4
                        color: _grantCloseMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                        AppIcons.AppIcon {
                            anchors.centerIn: parent
                            name: "close"; size: 10
                            iconColor: Theme.AppTheme.textMuted
                        }

                        MouseArea {
                            id: _grantCloseMA
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape:  Qt.PointingHandCursor
                            onClicked:    root._selectedGrantId = ""
                        }
                    }
                }

                // Inspector body
                Flickable {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    contentWidth:      width
                    contentHeight:     _grantInspector.implicitHeight
                    clip:              true
                    boundsBehavior:    Flickable.StopAtBounds

                    ColumnLayout {
                        id: _grantInspector
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.AppTheme.marginMd }
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            text:           root._selectedGrantItem ? (root._selectedGrantItem.title || "") : ""
                            color:          Theme.AppTheme.textPrimary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.sectionSize
                            font.bold:      true
                            wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                        }

                        AppWidgets.StatusChip {
                            visible: root._selectedGrantItem
                                ? (root._selectedGrantItem.statusLabel || "").length > 0 : false
                            status: root._selectedGrantItem ? (root._selectedGrantItem.statusLabel || "") : ""
                        }

                        Rectangle {
                            Layout.fillWidth:  true
                            Layout.topMargin:  2
                            Layout.bottomMargin: 2
                            height: 1; color: Theme.AppTheme.divider
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            visible: root._selectedGrantItem
                                ? (root._selectedGrantItem.subtitle || "").length > 0 : false

                            AppControls.Label {
                                text:           "Username"
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold:      true
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text:           root._selectedGrantItem ? (root._selectedGrantItem.subtitle || "") : ""
                                color:          Theme.AppTheme.textSecondary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            visible: root._selectedGrantItem
                                ? (root._selectedGrantItem.supportingText || "").length > 0 : false

                            AppControls.Label {
                                text:           "Permissions"
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold:      true
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text:           root._selectedGrantItem ? (root._selectedGrantItem.supportingText || "") : ""
                                color:          Theme.AppTheme.textSecondary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            visible: root._selectedGrantItem
                                ? (root._selectedGrantItem.metaText || "").length > 0 : false

                            AppControls.Label {
                                text:           "Assigned"
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold:      true
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text:           root._selectedGrantItem ? (root._selectedGrantItem.metaText || "") : ""
                                color:          Theme.AppTheme.textSecondary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.topMargin: 2
                            height: 1; color: Theme.AppTheme.divider
                            visible: root._selectedGrantItem !== null
                        }

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            visible:  root._selectedGrantItem !== null
                            text:     "Revoke Access"
                            iconName: "delete"
                            danger:   true
                            enabled:  root.controller ? !root.controller.isBusy : false
                            onClicked: {
                                if (root.controller && root._selectedGrantItem) {
                                    root.controller.removeMembership(root._selectedGrantItem.id || "")
                                    root._selectedGrantId = ""
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Account Security & Sessions ───────────────────────────────
    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Account Security & Sessions" }

    AppWidgets.ContextualActionToolbar {
        Layout.fillWidth: true
        visible:  root._selectedSessionItem !== null
        title:    root._selectedSessionItem ? (root._selectedSessionItem.title || "") : ""
        subtitle: root._selectedSessionItem ? (root._selectedSessionItem.supportingText || "") : ""
        busy:     root.controller ? root.controller.isBusy : false
        actions:  root._sessionActions
        onActionTriggered: function(actionId) {
            if (!root.controller || !root._selectedSessionItem) return
            const userId = root._selectedSessionItem.id || ""
            if      (actionId === "unlock") root.controller.unlockUser(userId)
            else if (actionId === "revoke") root.controller.revokeSessions(userId)
        }
    }

    AppWidgets.DataTable {
        id: _sessionsTable
        Layout.fillWidth:      true
        Layout.preferredHeight: 200
        sourceModel:   root.controller ? root.controller.securityUsersTableModel : null
        columns:       root._sessionsColumns
        emptyText:     root.controller ? (root.controller.securityUsers.emptyState || "No security records") : "No security records"
        selectedRowId: root._selectedSessionId
        onRowSelected:  function(rowId) { root._selectedSessionId = rowId }
        onRowActivated: function(rowId) { root._selectedSessionId = rowId }
    }
}
