"""Pre-release closeout: StatusChip's legacy text-driven auto-classification
has been removed entirely. StatusChip is domain-neutral -- it never infers a
tone from `status` text. The only supported contract is: caller supplies
`status` (display text) and `tone` (explicit semantic tone); an
unrecognized/empty tone fails safe to "neutral"."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_KEEPALIVE = []


def _make_chip(qapp, *, status: str = "", tone: str | None = None):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    tone_line = f'tone: "{tone}"' if tone is not None else ""
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


def test_all_five_semantic_tones_are_accepted(qapp) -> None:
    for tone in ("neutral", "info", "success", "warning", "danger"):
        chip = _make_chip(qapp, status="Custom Status", tone=tone)
        assert chip.property("_variant") == tone


def test_no_tone_supplied_defaults_to_neutral(qapp) -> None:
    """No auto-classification exists any more -- omitting `tone` is neutral,
    regardless of what `status` text is displayed."""
    chip = _make_chip(qapp, status="Approved")
    assert chip.property("_variant") == "neutral"
    assert chip.property("tone") == "neutral"


def test_invalid_tone_value_fails_safe_to_neutral_not_a_crash(qapp) -> None:
    chip = _make_chip(qapp, status="Whatever", tone="not-a-real-tone")
    assert chip.property("_variant") == "neutral"


def test_arbitrary_future_status_text_does_not_affect_tone(qapp) -> None:
    """A brand-new module's own status vocabulary ("in_transit", "quarantined",
    ...) has no meaning to StatusChip -- an explicit tone renders correctly
    regardless of what the status text says, since there is no classifier
    left to consult it."""
    chip = _make_chip(qapp, status="In Transit", tone="warning")
    assert chip.property("_variant") == "warning"
    assert chip.property("status") == "In Transit"

    chip2 = _make_chip(qapp, status="Quarantined", tone="warning")
    assert chip2.property("_variant") == "warning"


def test_changing_status_text_alone_cannot_change_semantic_appearance(qapp) -> None:
    """Two chips with the same tone but wildly different status text must
    render identically -- proving `status` text is never consulted for
    tone. And the same status text with two different explicit tones must
    render differently, proving the text has no residual influence."""
    chip_a = _make_chip(qapp, status="Rejected", tone="success")
    chip_b = _make_chip(qapp, status="Totally Fine", tone="success")
    assert chip_a.property("_variant") == chip_b.property("_variant") == "success"

    chip_c = _make_chip(qapp, status="Approved", tone="danger")
    chip_d = _make_chip(qapp, status="Approved", tone="success")
    assert chip_c.property("_variant") == "danger"
    assert chip_d.property("_variant") == "success"
    assert chip_c.property("_variant") != chip_d.property("_variant")


def test_legacy_classifier_properties_no_longer_exist(qapp) -> None:
    """The removed `_legacyVariant`/`_normalized` properties must not
    silently resurface -- QML returns an invalid QVariant for an unknown
    property rather than raising, so assert on that instead of an
    exception."""
    chip = _make_chip(qapp, status="Approved", tone="danger")
    assert chip.property("_legacyVariant") is None
    assert chip.property("_normalized") is None
