from __future__ import annotations

from src.core.application.global_overview.services.activity_visibility import is_activity_visible


def test_platform_activity_is_always_visible_even_with_no_accessible_modules():
    assert is_activity_visible("platform", accessible_module_codes=frozenset()) is True


def test_accessible_enterprise_module_activity_is_visible():
    assert (
        is_activity_visible(
            "project_management", accessible_module_codes=frozenset({"project_management"})
        )
        is True
    )


def test_inaccessible_enterprise_module_activity_is_hidden():
    assert (
        is_activity_visible("project_management", accessible_module_codes=frozenset()) is False
    )


def test_unknown_module_fails_closed():
    assert is_activity_visible("mystery_module", accessible_module_codes=frozenset()) is False
    assert (
        is_activity_visible("mystery_module", accessible_module_codes=frozenset({"other_module"}))
        is False
    )


__all__ = []
