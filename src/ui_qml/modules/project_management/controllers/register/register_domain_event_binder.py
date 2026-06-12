from __future__ import annotations


def bind_register_domain_events(controller) -> None:
    controller._subscribe_domain_change(
        "project",
        "register_scope",
        scope_code="project_management",
    )


__all__ = ["bind_register_domain_events"]
