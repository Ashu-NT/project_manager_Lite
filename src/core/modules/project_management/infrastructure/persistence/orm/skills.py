"""ORM models for resource skills, certifications, and task skill requirements."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class ResourceSkillORM(Base):
    __tablename__ = "resource_skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_code: Mapped[str] = mapped_column(String, nullable=False)
    skill_name: Mapped[str] = mapped_column(String, nullable=False)
    proficiency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="intermediate",
        server_default="intermediate",
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    __table_args__ = (
        UniqueConstraint("resource_id", "skill_code", name="ux_resource_skill_code"),
    )


Index("idx_skills_resource", ResourceSkillORM.resource_id)
Index("idx_skills_code", ResourceSkillORM.skill_code)


class ResourceCertificationORM(Base):
    __tablename__ = "resource_certifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    certification_code: Mapped[str] = mapped_column(String, nullable=False)
    certification_name: Mapped[str] = mapped_column(String, nullable=False)
    issued_date: Mapped[Optional[object]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[object]] = mapped_column(Date, nullable=True)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    certificate_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_certs_resource", ResourceCertificationORM.resource_id)
Index("idx_certs_code", ResourceCertificationORM.certification_code)
Index("idx_certs_expiry", ResourceCertificationORM.expiry_date)


__all__ = ["ResourceCertificationORM", "ResourceSkillORM"]
