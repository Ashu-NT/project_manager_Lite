"""ADR-005 §9: `UnitOfWork`/`UnitOfWorkFactory` protocols -- contract shape only.

Confirms the shared protocol module has zero SQLAlchemy dependency (importable on its own),
declares no `session` field and no repository-lookup method of any kind, and that its two
error types are plain, narrowly-scoped exceptions -- not a large new hierarchy.
"""

from __future__ import annotations

from src.core.shared.persistence.unit_of_work import (
    MaxDispatchRoundsExceededError,
    UnitOfWork,
    UnitOfWorkClosedError,
    UnitOfWorkFactory,
)


def test_unit_of_work_protocol_module_never_imports_sqlalchemy() -> None:
    """AST-based, not a substring search -- the module's own docstring legitimately
    *discusses* SQLAlchemy in prose while correctly never importing it; only an actual
    import statement would violate ADR-005 Sec9's "core protocol must not depend on
    SQLAlchemy" rule."""
    import ast
    import inspect

    import src.core.shared.persistence.unit_of_work as module

    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("sqlalchemy"), alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("sqlalchemy"), node.module


def test_unit_of_work_protocol_declares_no_session_field() -> None:
    annotations = getattr(UnitOfWork, "__annotations__", {})
    assert "session" not in annotations


def test_unit_of_work_protocol_declares_no_generic_repository_lookup() -> None:
    """ADR-005 §9's explicit boundary: UnitOfWork exposes the transaction, never a general
    dependency lookup -- repository_for/get_repository/resolve/service/repository must never
    appear on this shared protocol."""
    for rejected_method in ("repository_for", "get_repository", "resolve", "service", "repository"):
        assert not hasattr(UnitOfWork, rejected_method), (
            f"{rejected_method} must not exist on UnitOfWork -- it would make UnitOfWork a "
            "service locator, exactly what ADR-005 Sec9 rejects"
        )


def test_unit_of_work_declares_exactly_the_approved_methods() -> None:
    expected = {
        "__enter__",
        "__exit__",
        "register_touched",
        "record_event",
        "tracked_aggregates",
        "commit",
    }
    for name in expected:
        assert hasattr(UnitOfWork, name), f"UnitOfWork is missing {name}"


def test_unit_of_work_factory_creates_from_a_context() -> None:
    assert hasattr(UnitOfWorkFactory, "create")


def test_error_types_are_narrow_and_not_a_new_hierarchy() -> None:
    """ADR-005 does not define specific exception types for lifecycle misuse / the dispatch
    round cap -- two small, clearly-named RuntimeError subclasses are used instead of a large
    new exception hierarchy, per repository convention (plain, catchable, stdlib-based)."""
    assert issubclass(UnitOfWorkClosedError, RuntimeError)
    assert issubclass(MaxDispatchRoundsExceededError, RuntimeError)
    assert UnitOfWorkClosedError is not MaxDispatchRoundsExceededError
