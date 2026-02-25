from __future__ import annotations

import os


DEFAULT_GOVERNED_ACTIONS = {
    "baseline.create",
    "cost.add",
    "cost.update",
    "cost.delete",
    "dependency.add",
    "dependency.remove",
}


def is_governance_required(action: str) -> bool:
    mode = (os.getenv("PM_GOVERNANCE_MODE", "off") or "").strip().lower()
    if mode != "required":
        return False
    raw_actions = (os.getenv("PM_GOVERNANCE_ACTIONS", "") or "").strip()
    if not raw_actions:
        governed_actions = DEFAULT_GOVERNED_ACTIONS
    else:
        governed_actions = {
            item.strip().lower()
            for item in raw_actions.split(",")
            if item.strip()
        }
    return action.strip().lower() in governed_actions


__all__ = ["is_governance_required", "DEFAULT_GOVERNED_ACTIONS"]

