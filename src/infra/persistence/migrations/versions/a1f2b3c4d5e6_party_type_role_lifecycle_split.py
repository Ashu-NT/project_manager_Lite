"""Party: split the old single-valued `party_type` (which conflated
identity-type and business-role) into a real `party_type` identity axis
(ORGANIZATION/INDIVIDUAL) plus an additive `roles` column; split
`tax_registration_number` into `registration_number`/`tax_identifier`;
replace the `is_active` boolean with a `status` lifecycle column (sole
source of truth, never a second persisted `is_active` alongside it).

Revision ID: a1f2b3c4d5e6
Revises: f1c93b7e208d
Create Date: 2026-10-06 00:00:00.000000

Every existing Party predates this axis and is 100% real ORGANIZATION
usage today (per the Party enterprise-backbone audit) -- rows are
backfilled accordingly: the old `party_type` value becomes a `roles` tag
(SUPPLIER/MANUFACTURER/VENDOR/CONTRACTOR/SERVICE_PROVIDER carry straight
across; GENERAL had no real meaning beyond "no role selected" and is not
carried forward), and `party_type` itself becomes ORGANIZATION for every
row.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1f2b3c4d5e6'
down_revision: str | Sequence[str] | None = 'f1c93b7e208d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "parties"
_OLD_ROLE_VALUES = ("SUPPLIER", "MANUFACTURER", "VENDOR", "CONTRACTOR", "SERVICE_PROVIDER")


def upgrade() -> None:
    connection = op.get_bind()

    op.add_column(_TABLE, sa.Column("roles", sa.String(length=256), nullable=True))
    op.add_column(_TABLE, sa.Column("registration_number", sa.String(length=128), nullable=True))
    op.add_column(_TABLE, sa.Column("tax_identifier", sa.String(length=128), nullable=True))
    op.add_column(_TABLE, sa.Column("status", sa.String(length=16), nullable=True))

    # roles <- old party_type (only for the real role-shaped values)
    for role in _OLD_ROLE_VALUES:
        connection.execute(
            sa.text(f"UPDATE {_TABLE} SET roles = :role WHERE party_type = :role"),
            {"role": role},
        )
    connection.execute(sa.text(f"UPDATE {_TABLE} SET roles = '' WHERE roles IS NULL"))
    # registration_number <- old tax_registration_number (its original
    # apparent intent); tax_identifier starts empty (a genuinely new field).
    connection.execute(
        sa.text(f"UPDATE {_TABLE} SET registration_number = tax_registration_number")
    )
    # status <- old is_active
    connection.execute(
        sa.text(f"UPDATE {_TABLE} SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END")
    )
    # party_type becomes the new identity axis -- every existing row is
    # real ORGANIZATION usage today.
    connection.execute(sa.text(f"UPDATE {_TABLE} SET party_type = 'ORGANIZATION'"))

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "party_type",
            existing_type=sa.String(length=64),
            type_=sa.String(length=32),
            existing_server_default=None,
            server_default="ORGANIZATION",
            nullable=False,
        )
        batch_op.alter_column(
            "roles",
            existing_type=sa.String(length=256),
            nullable=False,
            server_default="",
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            nullable=False,
            server_default="active",
        )
        batch_op.drop_index("idx_parties_active")
        batch_op.drop_column("is_active")
        batch_op.drop_column("tax_registration_number")

    op.create_index("idx_parties_status", _TABLE, ["organization_id", "status"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()

    op.add_column(
        _TABLE,
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
    )
    op.add_column(_TABLE, sa.Column("tax_registration_number", sa.String(length=128), nullable=True))

    connection.execute(
        sa.text(f"UPDATE {_TABLE} SET is_active = CASE WHEN status = 'active' THEN 1 ELSE 0 END")
    )
    connection.execute(
        sa.text(f"UPDATE {_TABLE} SET tax_registration_number = registration_number")
    )
    # party_type reverts to the first role tag found (or GENERAL if none) --
    # lossy for a Party that gained multiple roles after this migration,
    # which is an inherent, unavoidable property of downgrading a
    # single-valued column back from a multi-valued one.
    for role in _OLD_ROLE_VALUES:
        connection.execute(
            sa.text(
                f"UPDATE {_TABLE} SET party_type = :role "
                "WHERE roles = :role OR roles LIKE :role_prefix OR roles LIKE :role_mid OR roles LIKE :role_suffix"
            ),
            {
                "role": role,
                "role_prefix": f"{role},%",
                "role_mid": f"%,{role},%",
                "role_suffix": f"%,{role}",
            },
        )
    connection.execute(sa.text(f"UPDATE {_TABLE} SET party_type = 'GENERAL' WHERE party_type = 'ORGANIZATION'"))

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default="1",
        )
        batch_op.alter_column(
            "party_type",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_server_default="ORGANIZATION",
            server_default=None,
            nullable=False,
        )
        batch_op.drop_index("idx_parties_status")
        batch_op.drop_column("status")
        batch_op.drop_column("roles")
        batch_op.drop_column("registration_number")
        batch_op.drop_column("tax_identifier")

    op.create_index("idx_parties_active", _TABLE, ["organization_id", "is_active"], unique=False)
