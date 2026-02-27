from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import traceback
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Mapping

from infra.path import user_data_dir
from infra.version import get_app_version

REDACTED = "<redacted>"
REDACTED_EMAIL = "<redacted-email>"

_TRACE_ID_CTX: ContextVar[str | None] = ContextVar("pm_trace_id", default=None)
_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "pwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "session",
    "private_key",
)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SECRET_PAIR_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|authorization)\b\s*[:=]\s*([^\s,;]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-~=+/]+")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_incident_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"inc-{stamp}-{uuid.uuid4().hex[:8]}"


def current_trace_id() -> str | None:
    value = _TRACE_ID_CTX.get()
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


@contextmanager
def bind_trace_id(trace_id: str | None) -> Iterator[str]:
    normalized = (trace_id or "").strip() or create_incident_id()
    token = _TRACE_ID_CTX.set(normalized)
    try:
        yield normalized
    finally:
        _TRACE_ID_CTX.reset(token)


def _normalize_key(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _is_sensitive_key(value: object) -> bool:
    key = _normalize_key(value)
    return any(part in key for part in _SENSITIVE_KEY_PARTS)


def redact_text(value: str) -> str:
    text = str(value or "")
    text = _EMAIL_PATTERN.sub(REDACTED_EMAIL, text)
    text = _SECRET_PAIR_PATTERN.sub(lambda m: f"{m.group(1)}={REDACTED}", text)
    text = _BEARER_PATTERN.sub(f"Bearer {REDACTED}", text)
    return text


def redact_value(value: Any, *, _depth: int = 0, _max_depth: int = 8) -> Any:
    if _depth >= _max_depth:
        return "<max-depth>"

    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return redact_text(str(value))
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                out[key_text] = REDACTED
            else:
                out[key_text] = redact_value(item, _depth=_depth + 1, _max_depth=_max_depth)
        return out
    if isinstance(value, tuple):
        return [redact_value(item, _depth=_depth + 1, _max_depth=_max_depth) for item in value]
    if isinstance(value, list):
        return [redact_value(item, _depth=_depth + 1, _max_depth=_max_depth) for item in value]
    if isinstance(value, set):
        return [
            redact_value(item, _depth=_depth + 1, _max_depth=_max_depth)
            for item in sorted(value, key=lambda v: str(v))
        ]
    return redact_text(str(value))


class TraceIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = current_trace_id() or "-"
        return True


class OperationalSupport:
    def __init__(self, events_path: str | Path | None = None) -> None:
        if events_path is None:
            events_path = user_data_dir() / "logs" / "support-events.jsonl"
        self._events_path = Path(events_path)
        self._events_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @property
    def events_path(self) -> Path:
        return self._events_path

    def new_incident_id(self) -> str:
        return create_incident_id()

    def emit_event(
        self,
        *,
        event_type: str,
        message: str,
        level: str = "INFO",
        trace_id: str | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> str:
        normalized_type = (event_type or "").strip() or "support.event"
        normalized_level = (level or "INFO").strip().upper()
        resolved_trace = (trace_id or current_trace_id() or self.new_incident_id()).strip()

        payload: dict[str, Any] = {
            "timestamp_utc": _utc_now_iso(),
            "event_type": normalized_type,
            "level": normalized_level,
            "trace_id": resolved_trace,
            "message": redact_text(message or ""),
            "app_version": get_app_version(),
            "pid": os.getpid(),
        }
        if data:
            payload["data"] = redact_value(dict(data))

        line = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        with self._lock:
            with self._events_path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.write("\n")
        return resolved_trace

    def capture_exception(
        self,
        *,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
        context: str,
        trace_id: str | None = None,
    ) -> str:
        stack = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        return self.emit_event(
            event_type="app.crash",
            level="ERROR",
            trace_id=trace_id,
            message=f"Unhandled exception in {context}: {exc_value}",
            data={
                "context": context,
                "exception_type": getattr(exc_type, "__name__", str(exc_type)),
                "stacktrace": stack,
            },
        )

    def read_events(self, *, trace_id: str | None = None) -> list[dict[str, Any]]:
        if not self._events_path.exists():
            return []
        expected = (trace_id or "").strip()
        events: list[dict[str, Any]] = []
        for line in self._events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if expected and str(payload.get("trace_id") or "").strip() != expected:
                continue
            events.append(payload)
        return events


_GLOBAL_SUPPORT: OperationalSupport | None = None
_HOOKS_INSTALLED = False


def get_operational_support() -> OperationalSupport:
    global _GLOBAL_SUPPORT
    if _GLOBAL_SUPPORT is None:
        _GLOBAL_SUPPORT = OperationalSupport()
    return _GLOBAL_SUPPORT


def install_global_exception_hooks(support: OperationalSupport | None = None) -> None:
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return

    recorder = support or get_operational_support()
    previous_sys_hook = sys.excepthook

    def _sys_hook(exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
        try:
            recorder.capture_exception(
                exc_type=exc_type,
                exc_value=exc_value,
                exc_traceback=exc_tb,
                context="main-thread",
            )
        except Exception:
            pass
        previous_sys_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _sys_hook

    previous_thread_hook = getattr(threading, "excepthook", None)
    if previous_thread_hook is not None:

        def _thread_hook(args: Any) -> None:
            thread_name = getattr(getattr(args, "thread", None), "name", "worker-thread")
            try:
                recorder.capture_exception(
                    exc_type=args.exc_type,
                    exc_value=args.exc_value,
                    exc_traceback=args.exc_traceback,
                    context=f"thread:{thread_name}",
                )
            except Exception:
                pass
            previous_thread_hook(args)

        threading.excepthook = _thread_hook

    _HOOKS_INSTALLED = True


__all__ = [
    "OperationalSupport",
    "REDACTED",
    "REDACTED_EMAIL",
    "TraceIdLogFilter",
    "bind_trace_id",
    "create_incident_id",
    "current_trace_id",
    "get_operational_support",
    "install_global_exception_hooks",
    "redact_text",
    "redact_value",
]
