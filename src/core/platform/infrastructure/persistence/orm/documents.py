"""Platform ORM models for document management."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.platform.org.domain import EmploymentType
from src.core.platform.time.domain import TimesheetPeriodStatus
from src.infra.persistence.orm.base import Base

class DocumentStructureORM(Base):
    __tablename__ = "document_structures"
    __table_args__ = (
        UniqueConstraint("organization_id", "structure_code", name="ux_document_structures_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    structure_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_structure_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("document_structures.id", ondelete="SET NULL"),
        nullable=True,
    )
    object_scope: Mapped[str] = mapped_column(String(128), nullable=False, default="GENERAL", server_default="GENERAL")
    default_document_type: Mapped[str] = mapped_column(String(64), nullable=False, default="GENERAL", server_default="GENERAL")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_document_structures_organization", DocumentStructureORM.organization_id)
Index("idx_document_structures_parent", DocumentStructureORM.parent_structure_id)


class DocumentORM(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "document_code", name="ux_documents_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_structure_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("document_structures.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_system: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confidentiality_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    business_version_label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_documents_organization", DocumentORM.organization_id)
Index("idx_documents_structure", DocumentORM.document_structure_id)
Index("idx_documents_uploaded_by", DocumentORM.uploaded_by_user_id)


class DocumentLinkORM(Base):
    __tablename__ = "document_links"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "module_code",
            "entity_type",
            "entity_id",
            "link_role",
            name="ux_document_links_unique",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_code: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    link_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


Index("idx_document_links_document", DocumentLinkORM.document_id)
Index(
    "idx_document_links_entity",
    DocumentLinkORM.organization_id,
    DocumentLinkORM.module_code,
    DocumentLinkORM.entity_type,
    DocumentLinkORM.entity_id,
)
