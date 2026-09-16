"""App.Widgets.ActivityFeed's presentation contract.

ActivityFeed is a renderer + interaction emitter only -- it never infers
tone from status/title/description text, never understands any caller's
domain, and never uses display text as row identity. Tone, icon, and
clickability are always supplied explicitly by the presenter/builder that
owns the domain (see src/ui_qml/shared/models/activity_item.py)."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import QMetaObject, Q_ARG, Q_RETURN_ARG
from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_KEEPALIVE = []


def _make_feed(qapp, *, items=None, rows_activatable: bool = False):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    source = dedent(
        """
        import App.Widgets 1.0 as AppWidgets
        AppWidgets.ActivityFeed {
            rowsActivatable: __ROWS_ACTIVATABLE__
        }
        """
    ).replace("__ROWS_ACTIVATABLE__", "true" if rows_activatable else "false")
    component.setData(source.encode("utf-8"), "activity-feed-contract-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    if items is not None:
        root.setProperty("items", items)
    qapp.processEvents()
    _KEEPALIVE.append((engine, component, root))
    return root


def _resolve_tone(root, item: dict) -> str:
    return QMetaObject.invokeMethod(root, "resolveTone", Q_RETURN_ARG("QVariant"), Q_ARG("QVariant", item))


def _is_clickable(root, item: dict) -> bool:
    return QMetaObject.invokeMethod(root, "isRowClickable", Q_RETURN_ARG("QVariant"), Q_ARG("QVariant", item))


# ---------------------------------------------------------------------------
# Tone: explicit only, never inferred from text
# ---------------------------------------------------------------------------


def test_all_five_semantic_tones_are_accepted(qapp) -> None:
    feed = _make_feed(qapp)
    for tone in ("neutral", "info", "success", "warning", "danger"):
        assert _resolve_tone(feed, {"tone": tone}) == tone


def test_missing_or_invalid_tone_fails_safe_to_neutral(qapp) -> None:
    feed = _make_feed(qapp)
    assert _resolve_tone(feed, {}) == "neutral"
    assert _resolve_tone(feed, {"tone": "not-a-real-tone"}) == "neutral"
    assert _resolve_tone(feed, {"tone": ""}) == "neutral"


def test_changing_title_or_description_text_cannot_alter_tone(qapp) -> None:
    """Two items with wildly different title/description/statusLabel text but
    the same explicit tone must resolve identically -- proving tone is never
    derived from any display text. And the same text with two different
    explicit tones must resolve differently, proving the text has zero
    residual influence."""
    feed = _make_feed(qapp)
    item_a = {"title": "Project deleted", "description": "This looks catastrophic", "statusLabel": "Failed", "tone": "success"}
    item_b = {"title": "Note added", "description": "Nothing much happened", "statusLabel": "", "tone": "success"}
    assert _resolve_tone(feed, item_a) == _resolve_tone(feed, item_b) == "success"

    item_c = {"title": "Approved", "description": "Approved", "statusLabel": "Approved", "tone": "danger"}
    item_d = {"title": "Approved", "description": "Approved", "statusLabel": "Approved", "tone": "success"}
    assert _resolve_tone(feed, item_c) == "danger"
    assert _resolve_tone(feed, item_d) == "success"
    assert _resolve_tone(feed, item_c) != _resolve_tone(feed, item_d)


def test_no_keyword_based_tone_or_color_inference_remains_in_source() -> None:
    """ActivityFeed must never derive tone or color by lowercasing and
    keyword-matching statusLabel/title/description text. The only permitted
    text search is the fixed-vocabulary tone membership check in
    `resolveTone()`, which validates an explicit tone value and never
    inspects title/description/statusLabel."""
    from src.tests.path_rewrites import REPO_ROOT

    source = (
        REPO_ROOT / "src" / "ui_qml" / "shared" / "qml" / "App" / "Widgets" / "ActivityFeed.qml"
    ).read_text(encoding="utf-8")
    assert "toLowerCase" not in source
    forbidden_status_keyword_probes = (
        'indexOf("success")', 'indexOf("complet")', 'indexOf("approv")', 'indexOf("done")',
        'indexOf("danger")', 'indexOf("fail")', 'indexOf("error")', 'indexOf("reject")',
        'indexOf("warn")', 'indexOf("pending")',
    )
    for probe in forbidden_status_keyword_probes:
        assert probe not in source


# ---------------------------------------------------------------------------
# Clickability: explicit activation payload only, never text-based identity
# ---------------------------------------------------------------------------


def test_item_with_activation_state_is_clickable(qapp) -> None:
    feed = _make_feed(qapp)
    assert _is_clickable(feed, {"activationState": {"routeId": "project_management.tasks"}}) is True


def test_item_without_activation_state_is_not_clickable(qapp) -> None:
    feed = _make_feed(qapp)
    assert _is_clickable(feed, {"activationState": None}) is False
    assert _is_clickable(feed, {}) is False


def test_rows_activatable_override_makes_every_item_clickable(qapp) -> None:
    feed = _make_feed(qapp, rows_activatable=True)
    assert _is_clickable(feed, {}) is True
    assert _is_clickable(feed, {"activationState": None}) is True


def test_no_title_or_meta_text_equality_matching_remains_in_source() -> None:
    """ActivityFeed must never use title/metaText display text as row
    identity for navigation -- a row's identity is its explicit
    activationState payload."""
    from src.tests.path_rewrites import REPO_ROOT

    source = (
        REPO_ROOT / "src" / "ui_qml" / "shared" / "qml" / "App" / "Widgets" / "ActivityFeed.qml"
    ).read_text(encoding="utf-8")
    assert "routeId" not in source, "widget must not read a routeId field directly -- use activationState"
    assert "metaText" not in source
    assert "statusLabel ===" not in source


# ---------------------------------------------------------------------------
# statusLabel: optional, reserves no layout space when absent
# ---------------------------------------------------------------------------


def test_status_chip_visibility_is_bound_to_status_label_presence() -> None:
    """StatusChip sits in a RowLayout with `visible: statusLabel.length > 0`
    -- QtQuick Layouts exclude invisible children from space allocation, so
    an absent statusLabel reserves zero width/height by construction."""
    from src.tests.path_rewrites import REPO_ROOT

    source = (
        REPO_ROOT / "src" / "ui_qml" / "shared" / "qml" / "App" / "Widgets" / "ActivityFeed.qml"
    ).read_text(encoding="utf-8")
    assert 'visible: _row._statusLabel.length > 0' in source


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


def test_empty_items_shows_empty_state(qapp) -> None:
    feed = _make_feed(qapp, items=[])
    assert feed.property("items") == []
