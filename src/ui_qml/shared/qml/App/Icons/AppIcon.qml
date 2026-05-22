import QtQuick
import App.Theme 1.0 as Theme

Item {
    id: root

    // Public API
    property string name:      "default"
    property color  iconColor: Theme.AppTheme.textSecondary
    property int    size:      16
    property bool   active:    false
    property bool   disabled:  false

    // Sizing follows the rendered glyph
    implicitWidth:  _glyph.implicitWidth
    implicitHeight: _glyph.implicitHeight

    opacity: root.disabled ? 0.38 : 1.0

    Behavior on opacity {
        NumberAnimation {
            duration: 150
        }
    }

    // Effective color
    readonly property color _effectiveColor: root.disabled
        ? Theme.AppTheme.textMuted
        : (root.active ? Theme.AppTheme.accent : root.iconColor)

    FontLoader {
        id: fluentRegular
        source: "qrc:/fonts/FluentRegular.ttf"
    }

    FontLoader {
        id: fluentFilled
        source: "qrc:/fonts/FluentFilled.ttf"
    }

    // Icon registry
    readonly property var _map: ({
        // Navigation and Shell
        "home":           "\uF480", // ic_fluent_home_20_regular
        "dashboard":      "\uF344", // ic_fluent_data_pie_20_regular
        "search":         "\uF68F", // ic_fluent_search_20_regular
        "settings":       "\uF6A9", // ic_fluent_settings_20_regular
        "notifications":  "\uF114", // ic_fluent_alert_20_regular
        "user":           "\uF5BD", // ic_fluent_person_20_regular
        "admin":          "\uE946", // ic_fluent_person_settings_20_regular
        "control":        "\uEAD7", // ic_fluent_shield_task_20_regular
        "menu":           "\uE8B0", // ic_fluent_panel_left_20_regular

        // Actions
        "add":            "\uF109", // ic_fluent_add_20_regular
        "edit":           "\uF3DD", // ic_fluent_edit_20_regular
        "delete":         "\uF34C", // ic_fluent_delete_20_regular
        "close":          "\uF369", // ic_fluent_dismiss_20_regular
        "refresh":        "\uF13D", // ic_fluent_arrow_clockwise_20_regular
        "filter":         "\uF406", // ic_fluent_filter_20_regular
        "export":         "\uF150", // ic_fluent_arrow_download_20_regular
        "import":         "\uF159", // ic_fluent_arrow_import_20_regular
        "approve":        "\uF298", // ic_fluent_checkmark_circle_20_regular
        "reject":         "\uF36D", // ic_fluent_dismiss_circle_20_regular
        "history":        "\uF47E", // ic_fluent_history_20_regular
        "reset":          "\uF19F", // ic_fluent_arrow_reset_20_regular
        "save":           "\uF67F", // ic_fluent_save_20_regular
        "view":           "\uE5F2", // ic_fluent_eye_20_regular
        "upload":         "\uF1A4", // ic_fluent_arrow_upload_20_regular
        "lock":           "\uE78F", // ic_fluent_lock_closed_20_regular
        "time":           "\uF2DD", // ic_fluent_clock_20_regular

        // Project Management
        "project":        "\uE156", // ic_fluent_board_20_regular
        "tasks":          "\uE35D", // ic_fluent_clipboard_task_20_regular
        "calendar":       "\uF23C", // ic_fluent_calendar_today_20_regular
        "resources":      "\uF5B8", // ic_fluent_people_team_20_regular
        "financials":     "\uF54F", // ic_fluent_money_20_regular
        "risk":           "\uE018", // ic_fluent_alert_badge_20_regular
        "portfolio":      "\uF1FC", // ic_fluent_briefcase_20_regular
        "register":       "\uF2C9", // ic_fluent_clipboard_20_regular
        "collaboration":  "\uF286", // ic_fluent_chat_20_regular
        "timesheets":     "\uED88", // ic_fluent_timer_20_regular

        // Maintenance
        "assets":         "\uF335", // ic_fluent_cube_20_regular
        "maintenance":    "\uEE86", // ic_fluent_wrench_20_regular
        "workflow":       "\uE1D9", // ic_fluent_branch_20_regular
        "reliability":    "\uE9E0", // ic_fluent_pulse_square_20_regular
        "planner":        "\uF21D", // ic_fluent_calendar_clock_20_regular

        // Inventory and Procurement
        "catalog":        "\uF462", // ic_fluent_grid_20_regular
        "inventory":      "\uE1BB", // ic_fluent_box_20_regular
        "reservations":   "\uF2C9", // ic_fluent_clipboard_20_regular
        "procurement":    "\uE2AC", // ic_fluent_cart_20_regular
        "pricing":        "\uF77C", // ic_fluent_tag_20_regular

        // Drawer navigation
        "chevron_down":   "\uF2A3", // ic_fluent_chevron_down_20_regular
        "chevron_up":     "\uF2B6", // ic_fluent_chevron_up_20_regular
        "chevron_right":  "\uF2AF", // ic_fluent_chevron_right_20_regular
        "chevron_left":   "\uF2A9", // ic_fluent_chevron_left_20_regular

        // Fallback
        "default":        "\uF133"  // ic_fluent_apps_20_regular
    })

    // Glyph renderer
    Text {
        id: _glyph

        anchors.centerIn: parent

        text: root._map[root.name] !== undefined
              ? root._map[root.name]
              : root._map["default"]

        color: root._effectiveColor

        font.family: root.active ? fluentFilled.name : fluentRegular.name
        font.pixelSize: root.size

        renderType: Text.NativeRendering

        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter

        Behavior on color {
            ColorAnimation {
                duration: 150
            }
        }
    }
}
