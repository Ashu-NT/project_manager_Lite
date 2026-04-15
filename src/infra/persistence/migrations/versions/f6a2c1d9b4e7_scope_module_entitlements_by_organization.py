"""scope module entitlements by organization

Revision ID: f6a2c1d9b4e7
Revises: e3b7d9a4c112
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a2c1d9b4e7"
down_revision = "e3b7d9a4c112"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _organization_seed_id() -> str | None:
    bind = op.get_bind()
    active = bind.execute(
        sa.text(
            "SELECT id FROM organizations "
            "WHERE is_active = 1 "
            "ORDER BY organization_code ASC "
            "LIMIT 1"
        )
    ).scalar()
    if active is not None:
        return str(active)
    first = bind.execute(
        sa.text(
            "SELECT id FROM organizations "
            "ORDER BY organization_code ASC "
            "LIMIT 1"
        )
    ).scalar()
    if first is None and _has_table("organizations"):
        first = "org-default"
        bind.execute(
            sa.text(
                "INSERT INTO organizations "
                "(id, organization_code, display_name, timezone_name, base_currency, is_active, version) "
                "VALUES (:id, :organization_code, :display_name, :timezone_name, :base_currency, 1, 1)"
            ),
            {
                "id": first,
                "organization_code": "DEFAULT",
                "display_name": "Default Organization",
                "timezone_name": "UTC",
                "base_currency": "EUR",
            },
        )
    return str(first) if first is not None else None


def upgrade() -> None:
    if not _has_table("organization_module_entitlements"):
        op.create_table(
            "organization_module_entitlements",
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("module_code", sa.String(length=128), nullable=False),
            sa.Column("licensed", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_org_module_entitlements_organization",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("organization_id", "module_code"),
        )
        op.create_index(
            "idx_org_module_entitlements_org",
            "organization_module_entitlements",
            ["organization_id"],
            unique=False,
        )

    if not _has_table("module_entitlements"):
        return

    organization_id = _organization_seed_id()
    if organization_id is not None:
        bind = op.get_bind()
        rows = bind.execute(
            sa.text(
                "SELECT module_code, licensed, enabled, updated_at "
                "FROM module_entitlements"
            )
        ).mappings().all()
        for row in rows:
            bind.execute(
                sa.text(
                    "INSERT INTO organization_module_entitlements "
                    "(organization_id, module_code, licensed, enabled, updated_at) "
                    "VALUES (:organization_id, :module_code, :licensed, :enabled, :updated_at)"
                ),
                {
                    "organization_id": organization_id,
                    "module_code": row["module_code"],
                    "licensed": row["licensed"],
                    "enabled": row["enabled"],
                    "updated_at": row["updated_at"],
                },
            )

    op.drop_table("module_entitlements")


def downgrade() -> None:
    if not _has_table("module_entitlements"):
        op.create_table(
            "module_entitlements",
            sa.Column("module_code", sa.String(length=128), nullable=False),
            sa.Column("licensed", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("module_code"),
        )

    if _has_table("organization_module_entitlements"):
        organization_id = _organization_seed_id()
        if organization_id is not None:
            bind = op.get_bind()
            rows = bind.execute(
                sa.text(
                    "SELECT module_code, licensed, enabled, updated_at "
                    "FROM organization_module_entitlements "
                    "WHERE organization_id = :organization_id"
                ),
                {"organization_id": organization_id},
            ).mappings().all()
            for row in rows:
                bind.execute(
                    sa.text(
                        "INSERT INTO module_entitlements "
                        "(module_code, licensed, enabled, updated_at) "
                        "VALUES (:module_code, :licensed, :enabled, :updated_at)"
                    ),
                    {
                        "module_code": row["module_code"],
                        "licensed": row["licensed"],
                        "enabled": row["enabled"],
                        "updated_at": row["updated_at"],
                    },
                )

        op.drop_index(
            "idx_org_module_entitlements_org",
            table_name="organization_module_entitlements",
        )
        op.drop_table("organization_module_entitlements")
