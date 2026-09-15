"""Phase H: StatusChip generalization -- an explicit caller-supplied `tone`
must be honored verbatim (no auto-classification), existing callers that
never set `tone` must keep their exact legacy auto-classified behavior, and
an unrecognized/future business-status string a new module supplies (with
an explicit tone) must render with that tone rather than silently falling
back to the hardcoded legacy vocabulary."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_KEEPALIVE = []


def _make_chip(qapp, *, status: str = "", tone: str = ""):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    tone_line = f'tone: "{tone}"' if tone else ""
    source = dedent(
        f"""
        import App.Widgets 1.0 as AppWidgets
        AppWidgets.StatusChip {{ status: "{status}"; {tone_line} }}
        """
    )
    component.setData(source.encode("utf-8"), "status-chip-tone-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    qapp.processEvents()
    _KEEPALIVE.append((engine, component, root))
    return root


def test_explicit_tone_overrides_status_text_entirely(qapp) -> None:
    """A future module's own status word ("in_transit") isn't in the legacy
    vocabulary at all -- with an explicit tone it renders correctly anyway,
    instead of silently falling through to neutral."""
    chip = _make_chip(qapp, status="In Transit", tone="warning")
    assert chip.property("_variant") == "warning"
    assert chip.property("status") == "In Transit"


def test_explicit_tone_wins_even_when_status_text_would_auto_classify_differently(qapp) -> None:
    """A caller that knows better than the legacy heuristic can say so --
    e.g. displaying "Approved" with a neutral tone in a context where
    "approved" shouldn't read as an affirmative success color."""
    chip = _make_chip(qapp, status="Approved", tone="neutral")
    assert chip.property("_variant") == "neutral"


def test_invalid_tone_value_fails_safe_to_neutral_not_a_crash(qapp) -> None:
    chip = _make_chip(qapp, status="Whatever", tone="not-a-real-tone")
    assert chip.property("_variant") == "neutral"


def test_no_tone_supplied_falls_back_to_legacy_classification(qapp) -> None:
    """Existing Platform/PM callers that never pass `tone` are unaffected --
    the exact same auto-classification as before."""
    chip = _make_chip(qapp, status="Approved")
    assert chip.property("_variant") == "success"
    assert chip.property("tone") == ""


def test_all_five_semantic_tones_are_accepted(qapp) -> None:
    for tone in ("neutral", "info", "success", "warning", "danger"):
        chip = _make_chip(qapp, status="Custom Status", tone=tone)
        assert chip.property("_variant") == tone
