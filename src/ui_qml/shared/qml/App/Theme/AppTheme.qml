pragma Singleton

import QtQuick

QtObject {
    readonly property string fontFamily: "Segoe UI Variable Text"

    // ── Surface hierarchy ──────────────────────────────────────
    readonly property color appBackground: "#F7F9FC"
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceAlt: "#EDF2F8"
    readonly property color surfaceRaised: "#FFFFFF"
    readonly property color surfaceSunken: "#F0F4F8"
    readonly property color hoverSurface: "#EBF2FA"
    readonly property color selectedSurface: "#D6E8F7"

    // ── Borders ────────────────────────────────────────────────
    readonly property color border: "#CCD6E3"
    readonly property color borderStrong: "#B8C5D6"
    readonly property color subtleBorder: "#E4ECF4"
    readonly property color divider: "#E4ECF4"
    readonly property color focusBorder: "#0A66A8"

    // ── Navigation surfaces ────────────────────────────────────
    readonly property color navBackground: "#EDF2F8"
    readonly property color navHoverBackground: "#DDE8F5"
    readonly property color navSelectedBackground: "#D6E8F7"
    readonly property color navSelectedText: "#0A66A8"

    // ── Text ───────────────────────────────────────────────────
    readonly property color textPrimary: "#16202B"
    readonly property color textSecondary: "#3C4A5C"
    readonly property color textMuted: "#5A6678"
    readonly property color textOnAccent: "#FFFFFF"

    // ── Accent ────────────────────────────────────────────────
    readonly property color accent: "#0A66A8"
    readonly property color accentHover: "#09578E"
    readonly property color accentPressed: "#074A78"
    readonly property color accentSoft: "#D6E8F7"

    // ── Semantic ──────────────────────────────────────────────
    readonly property color success: "#1E7F5A"
    readonly property color successSoft: "#E6F4EE"
    readonly property color warning: "#9A5A00"
    readonly property color warningSoft: "#FFF4E0"
    readonly property color danger: "#B3282D"
    readonly property color dangerSoft: "#FDEAEB"
    readonly property color info: "#0A66A8"
    readonly property color infoSoft: "#D6E8F7"

    // ── Spacing ───────────────────────────────────────────────
    readonly property int spacingXs: 4
    readonly property int spacingSm: 8
    readonly property int spacingMd: 12
    readonly property int spacingLg: 24
    readonly property int spacingXl: 32

    // ── Margins ───────────────────────────────────────────────
    readonly property int marginSm: 8
    readonly property int marginMd: 12
    readonly property int marginLg: 24
    readonly property int marginXl: 32

    // ── Radii ─────────────────────────────────────────────────
    readonly property int radiusSm: 4
    readonly property int radiusMd: 6
    readonly property int radiusLg: 10

    // ── Type scale ────────────────────────────────────────────
    readonly property int captionSize: 11
    readonly property int smallSize: 12
    readonly property int sectionTitleSize: 13
    readonly property int bodySize: 14
    readonly property int sectionSize: 16
    readonly property int titleSize: 20
    readonly property int headerSize: 24

    // ── Density ───────────────────────────────────────────────
    readonly property int compactRowHeight: 32
    readonly property int normalRowHeight: 40
    readonly property int toolbarHeight: 40
    readonly property int sidebarRowHeight: 36
}
