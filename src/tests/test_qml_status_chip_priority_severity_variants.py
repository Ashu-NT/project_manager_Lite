from __future__ import annotations

from textwrap import dedent

from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_KEEPALIVE = []


def _make_chip(qapp, status: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    source = dedent(
        f"""
        import App.Widgets 1.0 as AppWidgets
        AppWidgets.StatusChip {{ status: "{status}" }}
        """
    )
    component.setData(source.encode("utf-8"), "status-chip-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    qapp.processEvents()
    _KEEPALIVE.append((engine, component, root))
    return root


def test_priority_and_severity_words_get_real_tones_not_neutral(qapp):
    """Tasks' Priority column and Register's severity chip both display
    High/Medium/Low(/Critical) text; before these tokens were added, none
    of them matched any known status word, so every one silently rendered
    as a neutral gray chip regardless of actual priority/severity."""
    high = _make_chip(qapp, "High")
    medium = _make_chip(qapp, "Medium")
    low = _make_chip(qapp, "Low")
    critical = _make_chip(qapp, "Critical")
    unknown = _make_chip(qapp, "Some Unrelated Text")

    assert high.property("_variant") == "danger"
    assert medium.property("_variant") == "warning"
    assert low.property("_variant") == "info"
    assert critical.property("_variant") == "danger"
    assert unknown.property("_variant") == "neutral"


def test_infeasible_and_flexible_schedule_status_words_get_real_tones(qapp) -> None:
    """R4.4 constraint-aware backward CPM wiring: Task Detail -> Schedule
    Impact's Schedule Status chip renders the backend-owned
    "Infeasible"/"Critical"/"Flexible" precedence -- before "infeasible"/
    "flexible" were added to this vocabulary, both would have silently
    fallen to the neutral-gray default, defeating the whole point of a
    visually distinct infeasible state."""
    infeasible = _make_chip(qapp, "Infeasible")
    flexible = _make_chip(qapp, "Flexible")

    assert infeasible.property("_variant") == "danger"
    assert flexible.property("_variant") == "success"
