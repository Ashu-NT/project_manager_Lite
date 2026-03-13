"""Compatibility wrapper for audit repositories."""

from infra.platform.db.audit.repository import SqlAlchemyAuditLogRepository

__all__ = ["SqlAlchemyAuditLogRepository"]

