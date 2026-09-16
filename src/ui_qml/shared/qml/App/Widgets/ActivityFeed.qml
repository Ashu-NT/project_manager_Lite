pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons

// Reusable timeline activity feed -- renderer + interaction emitter ONLY.
// It never parses action text, never infers tone/meaning from title,
// description, or statusLabel, and never understands any caller's domain
// (project/task/organization/...). Every presentation decision -- title,
// description, icon, tone, actor display, timestamp formatting -- is made
// by the presenter/builder that owns the domain and handed to this widget
// already resolved. See src/ui_qml/shared/models/activity_item.py for the
// canonical Python-side shape this widget's `items` array mirrors.
//
// items: [{
//   id, title, description, supportingText, actorDisplay,
//   occurredAt, occurredAtLabel, iconKey, tone, subjectDisplay,
//   statusLabel, activationState
// }]
//
// - tone: one of "neutral" | "info" | "success" | "warning" | "danger",
//   supplied explicitly. Unrecognized/missing values fail safe to "neutral".
// - statusLabel is optional: leave "" for an ordinary event -- the badge is
//   omitted and reserves no layout space.
// - activationState: optional opaque navigation payload. A row is
//   clickable when this is present (non-null/undefined) or when the
//   feed-level `rowsActivatable` is set. This widget never inspects its
//   contents -- it hands the whole item back via itemActivated and the
//   caller's own handler resolves navigation.
Item {
    id: root

    property var    items:     []
    property string emptyText: "No activity recorded"
    // Opt-in: makes every row clickable regardless of a per-row
    // `activationState`, e.g. for a caller that navigates by row index.
    property bool   rowsActivatable: false

    signal itemActivated(var item)

    // Single source of truth for tone normalization -- an item's `tone` is
    // taken as-is when it's one of the five valid values, and forced to
    // "neutral" otherwise. Never consults title/description/statusLabel.
    function resolveTone(item) {
        const t = String((item && item.tone) || "")
        return ["neutral", "info", "success", "warning", "danger"].indexOf(t) >= 0 ? t : "neutral"
    }

    // A row is clickable when it carries a real activation payload (any
    // non-null value -- contents are never inspected here) or when the
    // whole feed opts every row in via `rowsActivatable`.
    function isRowClickable(item) {
        const activation = item ? item.activationState : undefined
        return (activation !== undefined && activation !== null) || root.rowsActivatable
    }

    function _toneBackground(tone) {
        switch (tone) {
            case "success": return Theme.AppTheme.successSoft
            case "info":    return Theme.AppTheme.infoSoft
            case "warning": return Theme.AppTheme.warningSoft
            case "danger":  return Theme.AppTheme.dangerSoft
            default:        return Theme.AppTheme.surfaceAlt
        }
    }

    function _toneForeground(tone) {
        switch (tone) {
            case "success": return Theme.AppTheme.success
            case "info":    return Theme.AppTheme.info
            case "warning": return Theme.AppTheme.warning
            case "danger":  return Theme.AppTheme.danger
            default:        return Theme.AppTheme.textSecondary
        }
    }

    implicitHeight: root.items.length === 0
        ? _empty.implicitHeight
        : _list.contentHeight

    AppWidgets.EmptyState {
        id: _empty
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width, 320)
        visible: root.items.length === 0
        title: root.emptyText
    }

    ListView {
        id: _list
        anchors.fill: parent
        visible: root.items.length > 0
        model: root.items
        interactive: false

        delegate: Item {
            id: _row
            required property var modelData
            required property int index

            width: _list.width
            // Content-driven, never a fixed magic number -- a row must
            // never be shorter than its own text needs, or adjacent rows
            // can visually overlap under real font metrics/DPI.
            height: Math.max(48, _rowColumn.implicitHeight + Theme.AppTheme.spacingXs * 2)

            readonly property string _title:           String(_row.modelData.title || "")
            readonly property string _description:     String(_row.modelData.description || "")
            readonly property string _supportingText:  String(_row.modelData.supportingText || "")
            readonly property string _actorDisplay:    String(_row.modelData.actorDisplay || "")
            readonly property string _occurredAtLabel: String(_row.modelData.occurredAtLabel || "")
            readonly property string _statusLabel:     String(_row.modelData.statusLabel || "")
            readonly property string _subjectDisplay:  String(_row.modelData.subjectDisplay || "")
            readonly property string _iconKey:         String(_row.modelData.iconKey || "history")
            readonly property string _tone:            root.resolveTone(_row.modelData)
            readonly property bool   _clickable:       root.isRowClickable(_row.modelData)

            readonly property string _footerText: [_row._subjectDisplay, _row._actorDisplay, _row._occurredAtLabel]
                .filter(part => part.length > 0)
                .join(" · ")

            activeFocusOnTab: _row._clickable
            Accessible.role: _row._clickable ? Accessible.Button : Accessible.StaticText
            Accessible.name: _row._clickable
                ? (_row._title + (_row._statusLabel.length > 0 ? ", " + _row._statusLabel : ""))
                : ""
            Accessible.onPressAction: if (_row._clickable) root.itemActivated(_row.modelData)

            Keys.onPressed: (event) => {
                if (!_row._clickable) {
                    return
                }
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                    root.itemActivated(_row.modelData)
                    event.accepted = true
                }
            }

            Rectangle {
                anchors.fill: parent
                visible: _row._clickable && (_row.activeFocus || _rowHover.hovered)
                color: Theme.AppTheme.hoverSurface
            }

            Rectangle {
                id: _badge
                anchors.left:       parent.left
                anchors.leftMargin: Theme.AppTheme.spacingSm
                anchors.top:        parent.top
                anchors.topMargin:  Theme.AppTheme.spacingXs
                width: 22; height: 22; radius: 11
                color: root._toneBackground(_row._tone)

                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name:      _row._iconKey
                    size:      13
                    iconColor: root._toneForeground(_row._tone)
                }
            }

            Rectangle {
                visible: _row.index < _list.count - 1
                anchors.horizontalCenter: _badge.horizontalCenter
                anchors.top:             _badge.bottom
                anchors.topMargin:       2
                anchors.bottom:          parent.bottom
                width: 1
                color: Theme.AppTheme.divider
            }

            ColumnLayout {
                id: _rowColumn
                anchors.left:        _badge.right
                anchors.leftMargin:  Theme.AppTheme.spacingSm
                anchors.right:       parent.right
                anchors.rightMargin: Theme.AppTheme.spacingSm
                anchors.top:         parent.top
                anchors.topMargin:   Theme.AppTheme.spacingXs
                spacing: 2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.Label {
                        Layout.fillWidth: true
                        text:           _row._title
                        color:          _row._clickable ? Theme.AppTheme.accent : Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold:      true
                        elide:          Text.ElideRight
                    }

                    AppWidgets.StatusChip {
                        // Reserves zero layout space when there is no real
                        // status/outcome to show -- ordinary events never
                        // get a badge just to fill this slot.
                        visible: _row._statusLabel.length > 0
                        status:  _row._statusLabel
                        tone:    _row._tone
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        _row._description.length > 0
                    text:           _row._description
                    color:          Theme.AppTheme.textSecondary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode:       Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        _row._supportingText.length > 0
                    text:           _row._supportingText
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.italic:    true
                    wrapMode:       Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        _row._footerText.length > 0
                    text:           _row._footerText
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    elide:          Text.ElideRight
                }
            }

            HoverHandler {
                id: _rowHover
                enabled: _row._clickable
                cursorShape: _row._clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
            }

            TapHandler {
                enabled: _row._clickable
                onTapped: root.itemActivated(_row.modelData)
            }
        }
    }
}
