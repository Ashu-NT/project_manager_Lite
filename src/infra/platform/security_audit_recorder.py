from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.authorization import SecurityDenialEvent
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.infra.platform.operational_support import current_trace_id


class DurableSecurityDenialRecorder:
    """Persist denial evidence in a transaction isolated from business work."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        trace_id_provider: Callable[[], str | None] = current_trace_id,
    ) -> None:
        self._session_factory = session_factory
        self._trace_id_provider = trace_id_provider

    @classmethod
    def for_session(
        cls,
        session: Session,
        *,
        trace_id_provider: Callable[[], str | None] = current_trace_id,
    ) -> "DurableSecurityDenialRecorder":
        factory = sessionmaker(
            bind=session.get_bind(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        return cls(factory, trace_id_provider=trace_id_provider)

    def record(self, event: SecurityDenialEvent) -> None:
        isolated_session = self._session_factory()
        try:
            repository = SqlAlchemyAuditRepository(isolated_session)
            tenant_id = _clean_optional(event.tenant_id)
            organization_id = (
                _clean_optional(event.organization_id)
                if tenant_id is not None
                else None
            )
            actor_user_id = _clean_optional(event.actor_user_id)
            session_id = _clean_optional(event.session_id)
            entry = AuditEntry.create(
                operation=_clean_text(
                    event.operation,
                    fallback="authorization.denied",
                    max_length=64,
                ),
                entity_type="authorization_decision",
                entity_id=session_id or actor_user_id or "anonymous",
                entity_parent_id=tenant_id,
                module="authorization",
                actor_id=actor_user_id,
                actor_type="user" if actor_user_id is not None else "anonymous",
                actor_username=_clean_optional(
                    event.actor_username,
                    max_length=128,
                ),
                tenant_id=tenant_id,
                organization_id=organization_id,
                request_id=_safe_trace_id(self._trace_id_provider),
                source="authorization",
                severity="high",
                compliance_tag="SOC2",
                metadata={
                    "action": _clean_text(
                        event.operation,
                        fallback="authorization.denied",
                        max_length=64,
                    ),
                    "outcome": "denied",
                    "reason_code": _clean_text(
                        event.reason_code,
                        fallback="PERMISSION_DENIED",
                    ),
                    "operation_label": _clean_text(
                        event.operation_label,
                        fallback="protected operation",
                    ),
                    "required_permissions": list(event.required_permissions),
                    "target_scope_type": _clean_optional(
                        event.target_scope_type
                    ),
                    "target_scope_id": _clean_optional(event.target_scope_id),
                },
            )
            if tenant_id is None:
                repository.add_platform(entry)
            else:
                repository.add_for_tenant(entry, tenant_id)
            isolated_session.commit()
        except Exception:
            isolated_session.rollback()
            raise
        finally:
            isolated_session.close()


def _safe_trace_id(
    provider: Callable[[], str | None],
) -> str | None:
    try:
        return _clean_optional(provider())
    except Exception:
        return None


def _clean_text(
    value: Any,
    *,
    fallback: str,
    max_length: int = 255,
) -> str:
    return str(value or "").strip()[:max_length] or fallback


def _clean_optional(
    value: Any,
    *,
    max_length: int = 255,
) -> str | None:
    return str(value or "").strip()[:max_length] or None


__all__ = ["DurableSecurityDenialRecorder"]
