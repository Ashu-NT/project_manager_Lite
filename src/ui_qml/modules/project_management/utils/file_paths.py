from __future__ import annotations

from urllib.parse import unquote, urlparse


def local_path_from_qml_file_url(value: str) -> str:
    """Normalize QML FileDialog URLs to local filesystem paths."""
    raw = (value or "").strip()
    if not raw:
        return ""
    if not raw.lower().startswith("file:"):
        return unquote(raw)

    parsed = urlparse(raw)
    path = unquote(parsed.path or "")
    if parsed.netloc and parsed.netloc.lower() != "localhost":
        return f"//{parsed.netloc}{path}"
    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        return path[1:]
    return path


__all__ = ["local_path_from_qml_file_url"]
