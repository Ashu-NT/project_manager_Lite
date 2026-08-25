"""LEGACY CHARACTERIZATION -- src/core/shared/events/signal.py's `Signal` primitive.

Pins down CURRENT behavior of the mechanism ADR-005's Platform migration will eventually
replace, so that a later phase can prove whether a behavior change is INTENTIONAL (called out
explicitly in ADR-005) or an ACCIDENTAL regression. These are characterization tests, not
endorsements -- where ADR-005 explicitly plans to change a behavior, each test's own docstring
says so.

Covers the four legacy behaviors the Platform implementation plan's P0 phase identifies:

  - depth-first-under-recursion dispatch (new here)
  - fail-fast propagation of generic, non-Qt-lifecycle exceptions, aborting remaining
    subscribers in that emit() call (new here -- the existing
    test_domain_events.py::test_signal_emit_keeps_non_deleted_runtime_errors_visible proves
    the exception propagates, but uses only one subscriber, so it does not prove a second,
    later subscriber is skipped)
  - Qt-deleted-object / stale-reference auto-pruning (the RuntimeError("... already deleted")
    variant is already characterized by
    test_domain_events.py::test_signal_emit_prunes_deleted_qt_like_callbacks -- this file adds
    only the previously-uncovered ReferenceError variant, to avoid duplicating existing
    coverage)
  - the absence of any logging inside Signal itself (new here)
"""

from __future__ import annotations

import logging

from src.core.shared.events.signal import Signal


def test_legacy_signal_dispatch_is_depth_first_under_recursion() -> None:
    """CHARACTERIZATION, NOT A GUARANTEE TO PRESERVE. ADR-005 Sec8 explicitly adopts
    breadth-first dispatch for the new PostCommitEventPublisher as a deliberate design
    change from this exact behavior -- this test exists so that change can later be proven
    deliberate, not accidental, when it lands in P2.
    """
    outer: Signal[str] = Signal()
    inner: Signal[str] = Signal()
    order: list[str] = []

    def _inner_handler(payload: str) -> None:
        order.append(f"inner:{payload}")

    def _outer_first(payload: str) -> None:
        order.append(f"outer-first:{payload}")
        # Re-entrant emit on a DIFFERENT signal, from inside a subscriber callback.
        inner.emit("nested")

    def _outer_second(payload: str) -> None:
        order.append(f"outer-second:{payload}")

    inner.connect(_inner_handler)
    outer.connect(_outer_first)
    outer.connect(_outer_second)

    outer.emit("top")

    # The nested emit() runs to full completion before the outer loop resumes with its
    # second subscriber -- depth-first, not breadth-first.
    assert order == ["outer-first:top", "inner:nested", "outer-second:top"]


def test_legacy_signal_generic_exception_aborts_remaining_subscribers() -> None:
    """CHARACTERIZATION, NOT A GUARANTEE TO PRESERVE. ADR-005 Sec16 explicitly adopts
    ISOLATE_AND_CONTINUE for the new PostCommitEventPublisher -- one handler's failure must
    not block sibling handlers. Signal.emit() today does the opposite for any exception
    type it does not specifically recognize as a Qt-lifecycle artifact: it propagates
    immediately, and the remaining subscribers registered for that emit() call never run.
    """
    signal: Signal[str] = Signal()
    calls: list[str] = []

    def _first_raises(_payload: str) -> None:
        calls.append("first")
        raise ValueError("not a Qt-lifecycle exception")

    def _second_never_runs(_payload: str) -> None:
        calls.append("second")

    signal.connect(_first_raises)
    signal.connect(_second_never_runs)

    raised = False
    try:
        signal.emit("x")
    except ValueError:
        raised = True

    assert raised, "Expected ValueError to propagate out of emit()"
    assert calls == ["first"], "the second subscriber must not run once the first raised"


def test_legacy_signal_prunes_reference_error() -> None:
    """CHARACTERIZATION -- the second, less-commonly-exercised auto-pruning path alongside
    the Qt-deleted-object RuntimeError case (already covered by
    test_domain_events.py::test_signal_emit_prunes_deleted_qt_like_callbacks). Both live in
    the same except-block set in Signal.emit() today.
    """
    signal: Signal[str] = Signal()
    seen: list[str] = []
    call_count = {"n": 0}

    def _gone(_payload: str) -> None:
        call_count["n"] += 1
        raise ReferenceError("weakly-referenced object no longer exists")

    def _ok(payload: str) -> None:
        seen.append(payload)

    signal.connect(_gone)
    signal.connect(_ok)

    signal.emit("first")
    signal.emit("second")

    assert call_count["n"] == 1, "the stale callback must be pruned after its first failure"
    assert seen == ["first", "second"]


def test_legacy_signal_emit_and_prune_do_not_log_anything(caplog) -> None:
    """CHARACTERIZATION of an absence: src/core/shared/events/signal.py contains zero
    logger calls today -- not on emit, not on connect/disconnect, not on stale-callback
    pruning. ADR-005 Sec18 (Observability) treats this as a real gap to close in the new
    mechanism, not a behavior to silently carry forward unexamined.
    """
    signal: Signal[str] = Signal()

    def _deleted(_payload: str) -> None:
        raise RuntimeError("Internal C++ object (SomeWidget) already deleted.")

    signal.connect(_deleted)

    with caplog.at_level(logging.DEBUG):
        signal.emit("x")

    assert caplog.records == []
