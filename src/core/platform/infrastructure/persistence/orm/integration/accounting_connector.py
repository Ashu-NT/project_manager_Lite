from sqlalchemy import Boolean, CheckConstraint, ForeignKeyConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class AccountingConnectorORM(Base):
    __tablename__ = "organization_accounting_connectors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version >= 1", name="ck_accounting_connector_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )
    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, primary_key=True)
    adapter_id: Mapped[str] = mapped_column(String(128), nullable=False)
    connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
