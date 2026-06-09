from __future__ import annotations


def bind_project_domain_events(controller) -> None:
    controller._subscribe_domain_change(
        "project",
        "portfolio_entity",
        scope_code="project_management",
    )


__all__ = ["bind_project_domain_events"]
