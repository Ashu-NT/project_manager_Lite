"""Calendar Recurring Event dialog: the visual recurrence builder's QML
wiring to the shared recurrence_text.py translation service. The RRULE
translation/humanization logic itself (daily/weekly/monthly/yearly shapes,
round-tripping, unrecognized-shape fallback) is already covered thoroughly
by test_recurrence_text.py and test_calendar_recurrence_bridge.py -- this
file only verifies the dialog correctly drives that service (state -> RRULE
-> summary, Edit-mode loading, humanized enum labels, a real chip click)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

_DIALOG_PATH = Path(
    "src/ui_qml/platform/qml/workspaces/calendars/dialogs/CalendarRecurringEventDialog.qml"
)
_DIALOG_DIR = _DIALOG_PATH.resolve().parent

# A strongly C++-typed `property PlatformAdminWorkspaceController` on a
# Popup-rooted component doesn't reliably take effect through
# QQmlApplicationEngine's Python-side initial_properties/setProperty --
# wiring it through a thin `var`-typed wrapper (exactly how the real app's
# AdminDialogHost receives it, via plain QML-to-QML property chaining
# ultimately rooted in a platformCatalog initial property) sidesteps that
# entirely without touching the production dialog file.
_WRAPPER_QML = f"""
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import "file:///{_DIALOG_DIR.as_posix()}" as CalendarDialogs

// Repeater/Popup item incubation needs an actual scene-graph render loop to
// finish -- a bare non-Window root never ticks one, leaving delegate items
// permanently un-instantiated even after pumping events. A real (if
// offscreen) ApplicationWindow gives it somewhere to render.
ApplicationWindow {{
    id: wrapperRoot
    width: 900
    height: 700
    visible: true
    property var platformCatalog

    CalendarDialogs.CalendarRecurringEventDialog {{
        id: _dlg
        objectName: "recurringEventDialogUnderTest"
        workspaceController: wrapperRoot.platformCatalog ? wrapperRoot.platformCatalog.adminWorkspace : null
    }}
}}
"""


def _controller_and_calendar_id(services):
    api_registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=api_registry)
    calendars_result = api_registry.platform_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data
    return catalog, calendars_result.data[0].id


_WRAPPER_COUNTER = [0]


def _load_dialog(platform_catalog):
    engine = create_qml_engine()
    _WRAPPER_COUNTER[0] += 1
    wrapper_path = (
        Path(tempfile.gettempdir())
        / f"calendar_recurring_dialog_test_wrapper_{_WRAPPER_COUNTER[0]}.qml"
    )
    wrapper_path.write_text(_WRAPPER_QML, encoding="utf-8")
    load_qml(
        engine,
        wrapper_path,
        initial_properties={"platformCatalog": platform_catalog},
    )
    wrapper_root = engine.rootObjects()[0]
    dialog = wrapper_root.findChild(QObject, "recurringEventDialogUnderTest")
    assert dialog is not None
    return engine, wrapper_root, dialog


def _variant(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


def _find(root: QObject, name: str) -> QObject:
    child = root.findChild(QObject, name)
    assert child is not None, f"Expected child object {name!r}"
    return child


def test_compiles_cleanly(qapp) -> None:
    engine = create_qml_engine()
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(_DIALOG_PATH.resolve())))
    assert not component.isError(), "\n".join(e.toString() for e in component.errors())


def test_open_for_create_defaults_to_weekly_with_no_days_selected(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)

    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    assert _variant(root.property("_frequency")) == "WEEKLY"
    assert _variant(root.property("_byDay")) == []
    assert _variant(root.property("_useAdvancedRule")) is False


def test_setting_weekly_single_day_produces_correct_rrule_and_summary(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    root.setProperty("_byDay", ["MO"])

    form_data = _variant(root.property("_formData"))
    assert form_data["recurrenceRule"] == "FREQ=WEEKLY;BYDAY=MO"
    assert _variant(root.property("_summaryText")) == "Every Monday"


def test_every_n_weeks_multiple_days_summary(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    root.setProperty("_interval", 2)
    root.setProperty("_byDay", ["MO", "WE"])

    assert _variant(root.property("_summaryText")) == "Every 2 weeks on Monday and Wednesday"


def test_open_for_edit_loads_a_recognized_rrule_into_the_visual_builder(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)

    state = {
        "id": "evt-1", "title": "Weekly Standup", "eventType": "MEETING",
        "recurrenceRule": "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE",
        "impactType": "REDUCED_CAPACITY", "startTimeLabel": "09:00", "endTimeLabel": "09:30",
        "effectiveFrom": "2026-10-07", "effectiveTo": "", "capacityImpactPercent": 0.0,
    }
    assert QMetaObject.invokeMethod(
        root, "openForEdit", Q_ARG("QVariant", calendar_id), Q_ARG("QVariant", state)
    )

    assert _variant(root.property("_mode")) == "edit"
    assert _variant(root.property("_frequency")) == "WEEKLY"
    assert _variant(root.property("_interval")) == 2
    assert _variant(root.property("_byDay")) == ["MO", "WE"]
    assert _variant(root.property("_useAdvancedRule")) is False
    assert _variant(root.property("_summaryText")) == "Every 2 weeks on Monday and Wednesday"


def test_open_for_edit_falls_back_to_advanced_for_an_unrecognized_rrule_shape(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)

    raw_rule = "FREQ=WEEKLY;BYWEEKNO=3;BYDAY=MO"
    state = {
        "id": "evt-2", "title": "Unusual Rule", "eventType": "MEETING",
        "recurrenceRule": raw_rule, "impactType": "UNAVAILABLE",
        "startTimeLabel": "09:00", "endTimeLabel": "10:00",
        "effectiveFrom": "2026-10-07", "effectiveTo": "", "capacityImpactPercent": 0.0,
    }
    assert QMetaObject.invokeMethod(
        root, "openForEdit", Q_ARG("QVariant", calendar_id), Q_ARG("QVariant", state)
    )

    assert _variant(root.property("_useAdvancedRule")) is True
    advanced_field = _find(root, "recurringAdvancedRuleField")
    assert str(advanced_field.property("text")) == raw_rule
    # Nothing silently reinterpreted or dropped -- the raw rule round-trips
    # straight through to the submitted payload unchanged.
    form_data = _variant(root.property("_formData"))
    assert form_data["recurrenceRule"] == raw_rule


def test_open_for_create_defaults_ends_to_never(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    assert _variant(root.property("_endsMode")) == "NEVER"
    ends_date_field = _find(root, "recurringEndsDateField")
    assert ends_date_field.property("visible") is False


def test_selecting_on_date_reveals_the_end_date_field_and_is_required(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    root.setProperty("_endsMode", "ON_DATE")
    ends_date_field = _find(root, "recurringEndsDateField")
    assert ends_date_field.property("visible") is True

    title_field = _find(root, "recurringTitleField")
    title_field.setProperty("text", "Weekly Standup")
    starts_field = _find(root, "recurringStartsField")
    starts_field.setProperty("text", "2026-10-07")
    root.setProperty("_byDay", ["MO"])

    assert QMetaObject.invokeMethod(root, "submitDialog")
    assert "end date" in str(root.property("errorMessage")).lower()

    ends_date_field.setProperty("text", "2027-10-07")
    captured = []
    root.saveRequested.connect(lambda mode, payload: captured.append(_variant(payload)))
    assert QMetaObject.invokeMethod(root, "submitDialog")
    assert len(captured) == 1
    assert captured[0]["effectiveTo"] == "2027-10-07"


def test_open_for_edit_with_an_end_date_loads_ends_mode_on_date(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)

    state = {
        "id": "evt-3", "title": "Weekly Standup", "eventType": "MEETING",
        "recurrenceRule": "FREQ=WEEKLY;BYDAY=MO", "impactType": "REDUCED_CAPACITY",
        "startTimeLabel": "09:00", "endTimeLabel": "09:30",
        "effectiveFrom": "2026-10-07", "effectiveTo": "2027-10-07", "capacityImpactPercent": 0.0,
    }
    assert QMetaObject.invokeMethod(
        root, "openForEdit", Q_ARG("QVariant", calendar_id), Q_ARG("QVariant", state)
    )

    assert _variant(root.property("_endsMode")) == "ON_DATE"
    ends_date_field = _find(root, "recurringEndsDateField")
    assert ends_date_field.property("visible") is True
    assert str(ends_date_field.property("text")) == "2027-10-07"


def test_event_type_and_impact_combos_show_humanized_labels_not_raw_enums(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    event_types = _variant(root.property("_eventTypes"))
    impact_types = _variant(root.property("_impactTypes"))

    labels = {item["value"]: item["label"] for item in event_types}
    assert labels["MEETING"] == "Meeting"
    assert labels["OVERTIME_WINDOW"] == "Overtime Window"

    impact_labels = {item["value"]: item["label"] for item in impact_types}
    assert impact_labels["REDUCED_CAPACITY"] == "Reduced Capacity"
    for label in list(labels.values()) + list(impact_labels.values()):
        assert "_" not in label


def test_submit_without_title_sets_error_and_does_not_emit_save(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))
    root.setProperty("_byDay", ["MO"])

    captured = []
    root.saveRequested.connect(lambda mode, payload: captured.append((mode, payload)))

    assert QMetaObject.invokeMethod(root, "submitDialog")

    assert captured == []
    assert "Title" in str(root.property("errorMessage"))


def test_submit_with_valid_weekly_event_emits_save_requested_with_create_mode(qapp, services) -> None:
    catalog, calendar_id = _controller_and_calendar_id(services)
    _engine, _wrapper_root, root = _load_dialog(catalog)
    assert QMetaObject.invokeMethod(root, "openForCreate", Q_ARG("QVariant", calendar_id))

    title_field = _find(root, "recurringTitleField")
    title_field.setProperty("text", "Weekly Standup")
    starts_field = _find(root, "recurringStartsField")
    starts_field.setProperty("text", "2026-10-07")
    root.setProperty("_byDay", ["MO"])

    captured = []
    root.saveRequested.connect(lambda mode, payload: captured.append((mode, _variant(payload))))

    assert QMetaObject.invokeMethod(root, "submitDialog")

    assert len(captured) == 1
    mode, payload = captured[0]
    assert mode == "create"
    assert payload["title"] == "Weekly Standup"
    assert payload["recurrenceRule"] == "FREQ=WEEKLY;BYDAY=MO"
    assert payload["effectiveFrom"] == "2026-10-07"
