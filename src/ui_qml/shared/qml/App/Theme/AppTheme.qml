pragma Singleton

import QtQuick

QtObject {
    readonly property string fontFamily: "Segoe UI Variable Text"

    readonly property color appBackground: "#F7F9FC"
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceAlt: "#EDF2F8"
    readonly property color border: "#CCD6E3"
    readonly property color borderStrong: "#B8C5D6"

    readonly property color textPrimary: "#16202B"
    readonly property color textSecondary: "#3C4A5C"
    readonly property color textMuted: "#5A6678"
    readonly property color textOnAccent: "#D0ECFF"

    readonly property color accent: "#0A66A8"
    readonly property color accentHover: "#09578E"
    readonly property color accentPressed: "#074A78"
    readonly property color accentSoft: "#D6E8F7"

    readonly property color success: "#1E7F5A"
    readonly property color warning: "#9A5A00"
    readonly property color danger: "#B3282D"

    readonly property int spacingXs: 4
    readonly property int spacingSm: 8
    readonly property int spacingMd: 12
    readonly property int spacingLg: 24

    readonly property int marginSm: 8
    readonly property int marginMd: 12
    readonly property int marginLg: 24
    readonly property int marginXl: 32

    readonly property int radiusSm: 8
    readonly property int radiusMd: 14
    readonly property int radiusLg: 22

    readonly property int bodySize: 14
    readonly property int smallSize: 12
    readonly property int titleSize: 22
}
