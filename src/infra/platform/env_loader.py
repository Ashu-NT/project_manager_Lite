from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_env_paths() -> tuple[Path, ...]:
    candidates: list[Path] = []
    if bool(getattr(sys, "frozen", False)):
        candidates.append(Path(sys.executable).resolve().parent / ".env")
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path(__file__).resolve().parents[3] / ".env")

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate.resolve(strict=False))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(candidate)
    return tuple(unique_candidates)


def resolve_env_file(path: str | Path | None = None) -> Path | None:
    if path is not None:
        candidate = Path(path).expanduser()
        return candidate if candidate.is_file() else None
    for candidate in _candidate_env_paths():
        if candidate.is_file():
            return candidate
    return None


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    if key.startswith("export "):
        key = key[7:].strip()
    if not key:
        return None

    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_env_file(path: str | Path | None = None, *, override: bool = False) -> Path | None:
    env_path = resolve_env_file(path)
    if env_path is None:
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value
    return env_path


__all__ = ["load_env_file", "resolve_env_file"]
