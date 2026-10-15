from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ConfigurationError
from src.infra.composition.app_container import build_service_graph


def test_runtime_bindings_reuse_module_owned_instances_without_database_work(session, monkeypatch):
    graph = build_service_graph(session)

    def forbidden_execute(*args, **kwargs):
        raise AssertionError("Exporting composed dependencies must not execute queries")

    monkeypatch.setattr(session, "execute", forbidden_execute)
    exports = graph.as_dict()

    assert graph.platform.session is session
    assert exports["session"] is session
    assert exports["authentication"] is graph.platform.auth.authentication
    assert exports["project_query"] is graph.project_management.project_query
    assert exports["task_lookup_query"] is graph.project_management.task_lookup_query
    assert exports["finance_governance_commands"] is graph.project_management.finance_governance_commands
    assert exports["module_registry"] is graph.integrations.module_registry
    assert exports["global_overview_desktop_api"] is graph.overview.global_overview_desktop_api
    assert not hasattr(graph, "task_lookup_query")
    assert not hasattr(type(graph), "__getattr__")


def test_runtime_binding_collision_fails_instead_of_overwriting_another_owner(session, monkeypatch):
    graph = build_service_graph(session)
    monkeypatch.setattr(
        type(graph.overview),
        "runtime_bindings",
        lambda self: {"project_query": object()},
    )

    with pytest.raises(ConfigurationError, match="project_query") as caught:
        graph.as_dict()

    assert caught.value.code == "DUPLICATE_RUNTIME_DEPENDENCY"
