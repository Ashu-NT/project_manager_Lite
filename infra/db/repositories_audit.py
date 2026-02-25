"""Compatibility wrapper for audit repositories."""

from infra.db.audit.repository import SqlAlchemyAuditLogRepository

__all__ = ["SqlAlchemyAuditLogRepository"]

