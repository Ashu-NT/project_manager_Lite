import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

// Compact, accessible multi-select chip/toggle -- built on QQC2.CheckBox so
// keyboard focus, Space/Enter toggle, and accessible checked/unchecked
// state all come for free; only the visual presentation is replaced (a
// pill-shaped toggle instead of a checkbox square + label). Reusable
// anywhere a wrapping multi-select chip group is needed -- not specific to
// any one entity's own option vocabulary. Selected-state color pairing
// (accentSoft background + accent text/border) matches DetailTabBar's own
// active-state treatment, the existing established pattern for this exact
// "soft accent fill with accent-colored content" combination.
QQC2.CheckBox {
    id: control

    leftPadding: Theme.AppTheme.spacingMd
    rightPadding: Theme.AppTheme.spacingMd
    topPadding: Theme.AppTheme.spacingXs
    bottomPadding: Theme.AppTheme.spacingXs
    spacing: Theme.AppTheme.spacingXs

    implicitHeight: Math.max(30, contentItem.implicitHeight + topPadding + bottomPadding)
    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding

    indicator: null

    background: Rectangle {
        radius: control.height / 2
        color: control.checked
            ? Theme.AppTheme.accentSoft
            : (control.hovered ? Theme.AppTheme.surfaceAlt : Theme.AppTheme.surfaceRaised)
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus
            ? Theme.AppTheme.focusBorder
            : control.checked
                ? Theme.AppTheme.accent
                : (control.hovered ? Theme.AppTheme.borderStrong : Theme.AppTheme.subtleBorder)

        Behavior on color { ColorAnimation { duration: 100 } }
        Behavior on border.color { ColorAnimation { duration: 100 } }
    }

    contentItem: RowLayout {
        spacing: Theme.AppTheme.spacingXs

        AppIcons.AppIcon {
            Layout.alignment: Qt.AlignVCenter
            visible: control.checked
            name: "approve"
            size: Theme.AppTheme.iconSm
            iconColor: Theme.AppTheme.accent
        }

        Text {
            Layout.alignment: Qt.AlignVCenter
            text: control.text
            color: control.checked ? Theme.AppTheme.accent : Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: control.checked
            wrapMode: Text.NoWrap
        }
    }
}
