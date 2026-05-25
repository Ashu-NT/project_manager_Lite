pragma Singleton

import QtQuick

QtObject {
    readonly property string fontFamily: "Segoe UI Variable Text"

    property string densityMode: "compact"

    readonly property bool compactDensity: densityMode !== "comfortable" && densityMode !== "spacious"
    readonly property bool comfortableDensity: densityMode === "comfortable"
    readonly property bool spaciousDensity: densityMode === "spacious"

    // Surface hierarchy
    readonly property color appBackground: "#F3F6FA"
    readonly property color background: appBackground
    readonly property color workspaceBackground: "#F7F8FA"
    readonly property color surface: "#FCFDFE"
    readonly property color surfaceAlt: "#EEF3F8"
    readonly property color surfaceRaised: "#FFFFFF"
    readonly property color surfaceSunken: "#E9EFF6"
    readonly property color surfaceOverlay: "#F6F7F9"
    readonly property color hoverSurface: "#EEF2F6"
    readonly property color selectedSurface: "#E4EDF7"

    // Borders and separators
    readonly property color border: "#CAD4DF"
    readonly property color borderStrong: "#B4C3D3"
    readonly property color subtleBorder: "#D3DCE6"
    readonly property color divider: "#D7E0E8"
    readonly property color focusBorder: "#0A66A8"
    readonly property color shadowColor: "#160A1B2A"
    readonly property color overlayScrim: "#4016202B"

    // Navigation
    readonly property color navBackground: "#E8EEF5"
    readonly property color navHoverBackground: "#DAE5F1"
    readonly property color navSelectedBackground: "#D3E4F8"
    readonly property color navSelectedText: "#0A5B95"
    readonly property color navMutedText: "#6A788A"

    // Text
    readonly property color textPrimary: "#17222D"
    readonly property color textSecondary: "#3D4B5D"
    readonly property color textMuted: "#667487"
    readonly property color textOnAccent: "#FFFFFF"

    // Accent
    readonly property color accent: "#0A66A8"
    readonly property color accentHover: "#09588F"
    readonly property color accentPressed: "#084B7A"
    readonly property color accentSoft: "#D8E7F7"

    // Semantic
    readonly property color success: "#1E7F5A"
    readonly property color successSoft: "#E7F4EE"
    readonly property color warning: "#9A5A00"
    readonly property color warningSoft: "#FEF2DE"
    readonly property color danger: "#B3282D"
    readonly property color dangerSoft: "#FDEBEC"
    readonly property color error: danger
    readonly property color info: "#0A66A8"
    readonly property color infoSoft: "#E2EEF9"

    // Spacing
    readonly property int spacingXs: 4
    readonly property int spacingSm: spaciousDensity ? 10 : 8
    readonly property int spacingMd: spaciousDensity ? 14 : comfortableDensity ? 12 : 10
    readonly property int spacingLg: spaciousDensity ? 28 : comfortableDensity ? 22 : 18
    readonly property int spacingXl: spaciousDensity ? 36 : comfortableDensity ? 30 : 24

    // Margins
    readonly property int marginSm: spaciousDensity ? 10 : 8
    readonly property int marginMd: spaciousDensity ? 16 : comfortableDensity ? 14 : 12
    readonly property int marginLg: spaciousDensity ? 28 : comfortableDensity ? 24 : 20
    readonly property int marginXl: spaciousDensity ? 36 : comfortableDensity ? 32 : 28

    // Radii
    readonly property int radiusSm: 4
    readonly property int radiusMd: 8
    readonly property int radiusLg: 12

    // Type scale
    readonly property int captionSize: 11
    readonly property int smallSize: 12
    readonly property int sectionTitleSize: 13
    readonly property int bodySize: 14
    readonly property int sectionSize: 16
    readonly property int titleSize: 20
    readonly property int headerSize: 24

    // Density-aware sizing
    readonly property int compactRowHeight: spaciousDensity ? 36 : comfortableDensity ? 34 : 30
    readonly property int normalRowHeight: spaciousDensity ? 44 : comfortableDensity ? 40 : 36
    readonly property int toolbarHeight: spaciousDensity ? 44 : comfortableDensity ? 40 : 36
    readonly property int sidebarRowHeight: spaciousDensity ? 40 : comfortableDensity ? 36 : 32
    readonly property int sidebarWidth: 248
    readonly property int sidebarCollapsedWidth: 52
    readonly property int headerHeight: spaciousDensity ? 58 : comfortableDensity ? 52 : 48
    readonly property int inputHeight: spaciousDensity ? 38 : comfortableDensity ? 36 : 32
    readonly property int panelHeaderHeight: spaciousDensity ? 48 : comfortableDensity ? 46 : 42
    readonly property int pagePadding: spaciousDensity ? 28 : comfortableDensity ? 24 : 20
    readonly property int sectionGap: spaciousDensity ? 20 : comfortableDensity ? 16 : 12
    readonly property int detailRailWidth: 220

    // Icon sizes
    readonly property int iconXs: 11
    readonly property int iconSm: 13
    readonly property int iconMd: 16
    readonly property int iconLg: 20
    readonly property int iconXl: 24

    // Context-specific icon sizes
    readonly property int navIconSize: 13
    readonly property int toolbarIconSize: 14
    readonly property int buttonIconSize: 12
    readonly property int tableIconSize: 13
    readonly property int headerIconSize: 16

    // Dialogs
    readonly property color dialogBackground: surfaceRaised
    readonly property color dialogBorder: subtleBorder
    readonly property color dialogHeaderBackground: surfaceOverlay
    readonly property color dialogFooterBackground: surface
    readonly property color dialogShadow: "#26000000"

    readonly property int dialogPadding: spaciousDensity ? 28 : comfortableDensity ? 24 : 20
    readonly property int dialogHeaderHeight: spaciousDensity ? 56 : comfortableDensity ? 52 : 48
    readonly property int dialogFooterHeight: spaciousDensity ? 64 : comfortableDensity ? 58 : 52
    readonly property int dialogMaxWidth: 920
    readonly property int dialogFormWidth: 640
    readonly property int dialogCompactWidth: 420

    // Tables
    readonly property int tableColumnCompactWidth: 120
    readonly property int tableColumnDefaultWidth: 160
    readonly property int tableColumnWideWidth: 220
    readonly property int tableStatusColumnWidth: 120
    readonly property int tableProgressColumnWidth: 150
}
