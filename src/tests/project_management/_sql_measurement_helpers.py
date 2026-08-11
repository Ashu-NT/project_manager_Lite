from __future__ import annotations

import functools
import re
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import event

_TABLE_NAME_RE = re.compile(r'(?:FROM|INTO|UPDATE|JOIN)\s+"?(\w+)"?', re.IGNORECASE)


@dataclass
class SqlStats:
    total_statements: int = 0
    total_db_time_s: float = 0.0
    by_table: Counter = field(default_factory=Counter)


@contextmanager
def measure_sql(session):
    engine = session.get_bind()
    stats = SqlStats()

    def _before(_conn, _cursor, _statement, _parameters, context, _executemany):
        context._measurement_started = time.perf_counter()

    def _after(_conn, _cursor, statement, _parameters, context, _executemany):
        stats.total_statements += 1
        stats.total_db_time_s += time.perf_counter() - context._measurement_started
        for table in set(_TABLE_NAME_RE.findall(statement)):
            stats.by_table[table] += 1

    event.listen(engine, "before_cursor_execute", _before)
    event.listen(engine, "after_cursor_execute", _after)
    try:
        yield stats
    finally:
        event.remove(engine, "before_cursor_execute", _before)
        event.remove(engine, "after_cursor_execute", _after)


@contextmanager
def count_calls(targets: list[tuple[object, str, str]]):
    counts: Counter = Counter()
    saved: list[tuple[object, str, object]] = []
    for instance, method_name, label in targets:
        original = getattr(instance, method_name)
        saved.append((instance, method_name, original))

        def _wrapper(*args, _original=original, _label=label, **kwargs):
            counts[_label] += 1
            return _original(*args, **kwargs)

        functools.update_wrapper(_wrapper, original)
        setattr(instance, method_name, _wrapper)
    try:
        yield counts
    finally:
        for instance, method_name, original in saved:
            setattr(instance, method_name, original)


__all__ = ["SqlStats", "count_calls", "measure_sql"]
