from __future__ import annotations

from datetime import datetime

from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass(frozen=True)
class AuthPolicyReconciliation:
    id: str
    policy_name: str
    from_version: int
    to_version: int
    change_set_hash: str
    applied_at: datetime
    applied_by_user_id: str
    rollback_json: str


__all__ = ["AuthPolicyReconciliation"]
