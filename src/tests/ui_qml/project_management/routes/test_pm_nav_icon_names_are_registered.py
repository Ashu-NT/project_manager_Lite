"""Direct product reports found three PM nav items referencing unregistered
icon names ("finance", "task", "resource" instead of the registered
"financials", "tasks", "resources") -- AppIcon.qml silently falls back to a
placeholder glyph rather than erroring, so these went unnoticed. This test
would have caught all three."""

from __future__ import annotations

import re
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

_ICON_KEY_RE = re.compile(r'"([a-zA-Z0-9_]+)"\s*:\s*"\\u[0-9A-Fa-f]{4}"')
_NAV_ICON_RE = re.compile(r'"icon"\s*:\s*"([a-zA-Z0-9_]+)"')


def _registered_icon_names() -> set[str]:
    path = (
        REPO_ROOT
        / "src"
        / "ui_qml"
        / "shared"
        / "qml"
        / "App"
        / "Icons"
        / "IconRegistry.js"
    )
    text = path.read_text(encoding="utf-8")
    return set(_ICON_KEY_RE.findall(text))


def test_pm_workspace_nav_icons_are_all_registered() -> None:
    path = (
        REPO_ROOT
        / "src"
        / "ui_qml"
        / "modules"
        / "project_management"
        / "controllers"
        / "common"
        / "pm_workspace_navigation_controller.py"
    )
    text = path.read_text(encoding="utf-8")
    referenced = set(_NAV_ICON_RE.findall(text))
    registered = _registered_icon_names()

    unregistered = referenced - registered
    assert not unregistered, (
        f"PM nav items reference unregistered icon names: {sorted(unregistered)}. "
        f"AppIcon.qml renders a silent fallback glyph for these instead of erroring, "
        f"so check IconRegistry.js for the actual key (e.g. singular vs plural)."
    )
