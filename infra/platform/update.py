from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

_DEFAULT_UPDATE_MANIFEST_SOURCE = (
    "https://github.com/Ashu-NT/project_manager_Lite/releases/latest/download/release-manifest.json"
)


@dataclass(frozen=True)
class UpdateRelease:
    version: str
    url: str | None
    notes: str | None
    sha256: str | None


@dataclass(frozen=True)
class UpdateCheckResult:
    channel: str
    current_version: str
    latest: UpdateRelease | None
    update_available: bool
    message: str


def default_update_manifest_source() -> str:
    env_override = (os.getenv("PM_UPDATE_MANIFEST_URL") or "").strip()
    return env_override or _DEFAULT_UPDATE_MANIFEST_SOURCE


def _parse_version(value: str) -> tuple[int, ...]:
    tokens = re.findall(r"\d+", str(value or ""))
    if not tokens:
        return (0,)
    return tuple(int(t) for t in tokens)


def _is_newer(candidate: str, current: str) -> bool:
    left = _parse_version(candidate)
    right = _parse_version(current)
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return left > right


def _read_manifest_text(source: str) -> str:
    raw = (source or "").strip()
    if not raw:
        raise ValueError("Manifest source is not configured.")

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        with urlopen(raw, timeout=10) as response:  # noqa: S310
            return response.read().decode("utf-8")
    if parsed.scheme == "file":
        path = Path(parsed.path)
        return path.read_text(encoding="utf-8")

    path = Path(raw)
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Manifest not found: {raw}")


def check_for_updates(
    *,
    current_version: str,
    channel: str,
    manifest_source: str,
) -> UpdateCheckResult:
    normalized_channel = (channel or "stable").strip().lower()
    try:
        payload = json.loads(_read_manifest_text(manifest_source))
    except Exception as exc:  # noqa: BLE001
        return UpdateCheckResult(
            channel=normalized_channel,
            current_version=current_version,
            latest=None,
            update_available=False,
            message=f"Update check failed: {exc}",
        )

    if not isinstance(payload, dict):
        return UpdateCheckResult(
            channel=normalized_channel,
            current_version=current_version,
            latest=None,
            update_available=False,
            message="Update check failed: manifest must be a JSON object.",
        )

    channels = payload.get("channels")
    if isinstance(channels, dict):
        selected = channels.get(normalized_channel) or channels.get("stable")
    else:
        selected = payload

    if not isinstance(selected, dict):
        return UpdateCheckResult(
            channel=normalized_channel,
            current_version=current_version,
            latest=None,
            update_available=False,
            message=f"No release entry found for channel '{normalized_channel}'.",
        )

    latest_version = str(selected.get("version") or "").strip()
    if not latest_version:
        return UpdateCheckResult(
            channel=normalized_channel,
            current_version=current_version,
            latest=None,
            update_available=False,
            message="Manifest is missing a valid release version.",
        )

    latest = UpdateRelease(
        version=latest_version,
        url=str(selected.get("url") or "").strip() or None,
        notes=str(selected.get("notes") or "").strip() or None,
        sha256=str(selected.get("sha256") or "").strip() or None,
    )
    update_available = _is_newer(latest.version, current_version)
    if update_available:
        message = f"Update available: {current_version} -> {latest.version}."
    else:
        message = f"Already up to date on {current_version}."

    return UpdateCheckResult(
        channel=normalized_channel,
        current_version=current_version,
        latest=latest,
        update_available=update_available,
        message=message,
    )


__all__ = [
    "UpdateCheckResult",
    "UpdateRelease",
    "check_for_updates",
    "default_update_manifest_source",
]
