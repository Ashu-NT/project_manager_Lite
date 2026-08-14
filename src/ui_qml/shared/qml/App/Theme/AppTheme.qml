pragma Singleton

import QtQuick

QtObject {
    id: root

    readonly property string fontFamily: "Segoe UI Variable Text"

    property string densityMode: "compact"

    readonly property bool compactDensity: densityMode !== "comfortable" && densityMode !== "spacious"
    readonly property bool comfortableDensity: densityMode === "comfortable"
    readonly property bool spaciousDensity: densityMode === "spacious"

    property string themeMode: "light"
    readonly property bool darkMode: themeMode === "dark"

    // Surface hierarchy
    readonly property color appBackground: root.darkMode ? "#1B1F24" : "#F3F6FA"
    readonly property color background: appBackground
    readonly property color workspaceBackground: root.darkMode ? "#1F242A" : "#F7F8FA"
    readonly property color surface: root.darkMode ? "#22282F" : "#FCFDFE"
    readonly property color surfaceAlt: root.darkMode ? "#262D35" : "#EEF3F8"
    readonly property color surfaceRaised: root.darkMode ? "#2A323B" : "#FFFFFF"
    readonly property color surfaceSunken: root.darkMode ? "#181C21" : "#E9EFF6"
    readonly property color surfaceOverlay: root.darkMode ? "#2E363F" : "#F6F7F9"
    readonly property color hoverSurface: root.darkMode ? "#323B45" : "#EEF2F6"
    readonly property color selectedSurface: root.darkMode ? "#243447" : "#E4EDF7"

    // Borders and separators
    readonly property color border: root.darkMode ? "#3A434D" : "#CAD4DF"
    readonly property color borderStrong: root.darkMode ? "#4A5560" : "#B4C3D3"
    readonly property color subtleBorder: root.darkMode ? "#333B44" : "#D3DCE6"
    readonly property color divider: root.darkMode ? "#343C45" : "#D7E0E8"
    readonly property color focusBorder: root.darkMode ? "#4CA3E0" : "#0A66A8"
    readonly property color shadowColor: root.darkMode ? "#33000000" : "#160A1B2A"
    readonly property color overlayScrim: root.darkMode ? "#66000000" : "#4016202B"

    // Elevation (shadow-based layering; QML has no native box-shadow, so
    // these are conventions for Rectangle-based drop-shadow effects layered
    // beneath raised surfaces)
    readonly property color elevationLowShadow: shadowColor
    readonly property color elevationMediumShadow: root.darkMode ? "#4D000000" : "#20000000"
    readonly property color elevationHighShadow: root.darkMode ? "#66000000" : dialogShadow
    readonly property int elevationLowBlur: 4
    readonly property int elevationMediumBlur: 10
    readonly property int elevationHighBlur: 18

    // Border widths
    readonly property int borderWidthThin: 1
    readonly property int borderWidthMedium: 2

    // Navigation
    readonly property color navBackground: root.darkMode ? "#20262D" : "#E8EEF5"
    readonly property color navHoverBackground: root.darkMode ? "#2B333C" : "#DAE5F1"
    readonly property color navSelectedBackground: root.darkMode ? "#28405A" : "#D3E4F8"
    readonly property color navSelectedText: root.darkMode ? "#6FB3E8" : "#0A5B95"
    readonly property color navMutedText: root.darkMode ? "#8B97A6" : "#6A788A"

    // Text
    readonly property color textPrimary: root.darkMode ? "#E7ECF2" : "#17222D"
    readonly property color textSecondary: root.darkMode ? "#B7C1CD" : "#3D4B5D"
    readonly property color textMuted: root.darkMode ? "#8B97A6" : "#667487"
    readonly property color textOnAccent: "#FFFFFF"

    // Accent
    readonly property color accent: root.darkMode ? "#4CA3E0" : "#0A66A8"
    readonly property color accentHover: root.darkMode ? "#5FB0E8" : "#09588F"
    readonly property color accentPressed: root.darkMode ? "#3D8AC4" : "#084B7A"
    readonly property color accentSoft: root.darkMode ? "#1E3A52" : "#D8E7F7"
    readonly property color accentSoftForeground: root.darkMode ? "#E7ECF2" : "#FFFFFF"

    // Semantic
    readonly property color success: root.darkMode ? "#4CBE8C" : "#1E7F5A"
    readonly property color successSoft: root.darkMode ? "#1B3A2C" : "#E7F4EE"
    readonly property color warning: root.darkMode ? "#E0A94C" : "#9A5A00"
    readonly property color warningSoft: root.darkMode ? "#3F3320" : "#FEF2DE"
    readonly property color danger: root.darkMode ? "#E56A6E" : "#B3282D"
    readonly property color dangerSoft: root.darkMode ? "#3F2426" : "#FDEBEC"
    readonly property color error: danger
    readonly property color info: root.darkMode ? "#4CA3E0" : "#0A66A8"
    readonly property color infoSoft: root.darkMode ? "#1E3145" : "#E2EEF9"

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
    readonly property int subtitleSize: 18
    readonly property int headerSize: 24

    // Typography roles -- semantic names for the type scale above, so
    // feature QML can bind to "what this text is" rather than a raw size.
    readonly property int typePageTitleSize: headerSize
    readonly property int typeSectionHeadingSize: sectionSize
    readonly property int typeBodySize: bodySize
    readonly property int typeSupportingTextSize: smallSize
    readonly property int typeMetadataSize: captionSize
    readonly property int typeTableTextSize: smallSize
    readonly property int typeFormLabelSize: smallSize
    readonly property int typeButtonTextSize: smallSize

    readonly property int weightRegular: Font.Normal
    readonly property int weightMedium: Font.Medium
    readonly property int weightSemibold: Font.DemiBold

    // Sizing
    readonly property int sizeXs: 16
    readonly property int sizeSm: 24
    readonly property int sizeMd: 32
    readonly property int sizeLg: 40
    readonly property int sizeXl: 48
    readonly property int size2Xl: 64
    readonly property int size3Xl: 96

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

    readonly property int navRailExpandedWidth: detailRailWidth
    readonly property int navRailCollapsedWidth: 48

    // R7.3/R7.4: responsive breakpoints, both keyed off the top-level window
    // width (via the Window attached property, not a page's own post-nav-
    // chrome width, which would double-subtract chrome and misfire).
    // narrowLayoutBreakpoint: below this, nav rails auto-collapse to
    // icon-only, reclaiming chrome before anything else degrades.
    // compactContentBreakpoint: the hard minimum (D8) -- below this, the
    // inspector collapses and lower-priority table columns hide.
    readonly property int narrowLayoutBreakpoint: 1280
    readonly property int compactContentBreakpoint: 1024

    // Inspector panel (list -> inspector -> detail pattern). Matches the
    // width AdminEntityDetailPanel.qml is already given today
    // (AdminConsolePage.qml's Layout.preferredWidth: 288).
    readonly property int inspectorWidth: 288

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

    // Semantic soft borders (derived from semantic colors)
    readonly property color dangerSoftBorder: Qt.rgba(danger.r, danger.g, danger.b, 0.30)
    readonly property color successSoftBorder: Qt.rgba(success.r, success.g, success.b, 0.30)
    readonly property color warningSoftBorder: Qt.rgba(warning.r, warning.g, warning.b, 0.30)

    // Login / Auth screen branding
    readonly property color loginWindowBackground:    "#0F1117"
    readonly property color loginBrandGradientStart:  "#0D1B3E"
    readonly property color loginBrandGradientEnd:    "#1A3461"
    readonly property color loginBrandRing1:          Qt.rgba(1, 1, 1, 0.05)
    readonly property color loginBrandRing2:          Qt.rgba(1, 1, 1, 0.04)
    readonly property color loginBrandSubtitle:       Qt.rgba(1, 1, 1, 0.55)
    readonly property color loginBrandFeatureText:    Qt.rgba(1, 1, 1, 0.60)
    readonly property color loginBrandFooter:         Qt.rgba(1, 1, 1, 0.25)
    readonly property color loginSpinnerBorder:       Qt.rgba(1, 1, 1, 0.70)

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

    // Dialog width tiers (R6): three sizes by content need, replacing the
    // 8 distinct per-dialog literal widths the audit found.
    readonly property int dialogWidthCompact: 440
    readonly property int dialogWidthStandard: 560
    readonly property int dialogWidthWide: 660

    // Tables
    readonly property int tableColumnCompactWidth: 120
    readonly property int tableColumnDefaultWidth: 160
    readonly property int tableColumnWideWidth: 220
    readonly property int tableStatusColumnWidth: 120
    readonly property int tableProgressColumnWidth: 150
}
