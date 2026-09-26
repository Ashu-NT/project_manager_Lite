"""Pre-release closeout: StatusChip's legacy text classifier (which used to
give "High"/"Critical"/"Infeasible"/etc. real tones without an explicit
`tone`) has been removed. StatusChip itself must render these words as
neutral when no tone is supplied; the actual priority/severity/schedule-state
semantics now live at their real callers (ActionCenterRow's priority tone
map, TasksScheduleImpactSection's backend-boolean-driven tone), which this
file also proves directly."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_KEEPALIVE = []


def _make_chip(qapp, status: str, tone: str | None = None):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    tone_line = f'tone: "{tone}"' if tone is not None else ""
    source = dedent(
        f"""
        import App.Widgets 1.0 as AppWidgets
        AppWidgets.StatusChip {{ status: "{status}"; {tone_line} }}
        """
    )
    component.setData(source.encode("utf-8"), "status-chip-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    qapp.processEvents()
    _KEEPALIVE.append((engine, component, root))
    return root


def test_priority_and_severity_words_render_neutral_without_an_explicit_tone(qapp):
    """StatusChip itself has no business vocabulary -- "High"/"Critical" and
    similar words carry no meaning to it any more. Real priority/severity
    tone now comes from the caller (see ActionCenterRow, DataTable status
    columns), never from StatusChip inspecting this text."""
    for word in ("High", "Medium", "Low", "Critical", "Infeasible", "Flexible", "Some Unrelated Text"):
        chip = _make_chip(qapp, word)
        assert chip.property("_variant") == "neutral", word


def _make_action_center_row(qapp, priority_label: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    source = dedent(
        f"""
        import App.Widgets 1.0 as AppWidgets
        AppWidgets.ActionCenterRow {{ title: "Item"; priorityLabel: "{priority_label}" }}
        """
    )
    component.setData(source.encode("utf-8"), "action-center-row-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    qapp.processEvents()
    _KEEPALIVE.append((engine, component, root))
    return root


def test_action_center_row_maps_priority_to_tone_locally(qapp):
    """ActionCenterRow owns cross-module action-priority semantics -- this
    is the real replacement for the old StatusChip legacy classification of
    High/Medium/Low."""
    assert _make_action_center_row(qapp, "High").property("_priorityTone") == "danger"
    assert _make_action_center_row(qapp, "Critical").property("_priorityTone") == "danger"
    assert _make_action_center_row(qapp, "Medium").property("_priorityTone") == "warning"
    assert _make_action_center_row(qapp, "Low").property("_priorityTone") == "info"
    assert _make_action_center_row(qapp, "Not set").property("_priorityTone") == "neutral"
