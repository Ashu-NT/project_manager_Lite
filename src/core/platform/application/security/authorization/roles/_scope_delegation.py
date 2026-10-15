from __future__ import annotations

import hashlib
import json

DEFAULT_SCOPE_DELEGATIONS: tuple[tuple[str, str, str], ...] = (
    ("access_admin", "project_viewer", "project"),
    ("access_admin", "project_contributor", "project"),
    ("access_admin", "project_lead", "project"),
    ("access_admin", "project_owner", "project"),
    ("access_admin", "site_viewer", "site"),
    ("access_admin", "site_operator", "site"),
    ("access_admin", "site_manager", "site"),
    ("access_admin", "storeroom_viewer", "storeroom"),
    ("access_admin", "storeroom_operator", "storeroom"),
    ("access_admin", "storeroom_manager", "storeroom"),
)


def _catalog_hash(catalog: tuple[tuple[str, str, str], ...]) -> str:
    canonical = json.dumps(list(catalog), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
