from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SeparationOfDutiesRule:
    required_permissions: frozenset[str]
    message: str


class SeparationOfDutiesPolicy:
    def __init__(self, rules: Iterable[SeparationOfDutiesRule] | None = None) -> None:
        self._rules = tuple(rules or default_separation_of_duties_rules())

    def find_conflicts(self, permission_codes: Iterable[str]) -> list[str]:
        normalized_permissions = {
            str(permission_code).strip()
            for permission_code in permission_codes
            if str(permission_code).strip()
        }
        messages: list[str] = []
        for rule in self._rules:
            if rule.required_permissions.issubset(normalized_permissions):
                messages.append(rule.message)
        return messages

    @property
    def rules(self) -> tuple[SeparationOfDutiesRule, ...]:
        return self._rules


def default_separation_of_duties_rules() -> tuple[SeparationOfDutiesRule, ...]:
    return (
        SeparationOfDutiesRule(
            required_permissions=frozenset({"approval.request", "approval.decide"}),
            message="Users cannot both request and decide the same governed approvals.",
        ),
        SeparationOfDutiesRule(
            required_permissions=frozenset({"access.manage", "security.manage"}),
            message="Users cannot both manage scoped access and manage login security controls.",
        ),
    )


def find_separation_of_duties_conflicts(permission_codes: Iterable[str]) -> list[str]:
    return SeparationOfDutiesPolicy().find_conflicts(permission_codes)


__all__ = [
    "SeparationOfDutiesPolicy",
    "SeparationOfDutiesRule",
    "default_separation_of_duties_rules",
    "find_separation_of_duties_conflicts",
]
