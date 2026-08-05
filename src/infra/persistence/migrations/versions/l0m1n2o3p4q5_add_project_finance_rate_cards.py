"""add project finance rate cards (ADR-PF-005)

Revision ID: l0m1n2o3p4q5
Revises: k9l0m1n2o3p4
Create Date: 2026-08-05
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "l0m1n2o3p4q5"
down_revision = "k9l0m1n2o3p4"
branch_labels = None
depends_on = None


_TABLES = (
    "project_finance_rate_card_lines",
    "project_finance_rate_cards",
)

# Same frozen ISO 4217 List One (2026-01-01) used by j8k9l0m1n2o3's profile
# backfill — kept self-contained per this repo's migration convention.
_SUPPORTED_CURRENCY_CODES = frozenset(
    """
    AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BOV
    BRL BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP
    CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF
    GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR
    KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT
    MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN
    PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE
    SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX
    USD USN UYI UYW UYU UZS VED VES VND VUV WST XAD XAF XCD XCG XOF XPF YER
    ZAR ZMW ZWG
    """.split()
)

# Resource.hourly_rate was always read with no date-scoping at all — any
# historical as_of date could see it. Seeding the backfilled legacy line's
# effective_from as this migration's own run date would make every report
# as_of before that date suddenly find "no applicable rate" where today it
# successfully reads Resource.hourly_rate. A fixed historical epoch instead
# of the run date is what keeps every pre-existing historical report intact.
LEGACY_RATE_BACKFILL_EFFECTIVE_FROM = date(1970, 1, 1)


def _backfill_legacy_rate_lines(bind) -> None:
    resources = bind.execute(
        sa.text(
            "SELECT r.id, r.tenant_id, r.organization_id, r.hourly_rate, r.currency_code, "
            "o.base_currency "
            "FROM resources r JOIN organizations o ON o.id = r.organization_id "
            "AND o.tenant_id = r.tenant_id "
            "WHERE r.tenant_id IS NOT NULL AND r.organization_id IS NOT NULL"
        )
    ).mappings()
    now = datetime.now(timezone.utc)
    card_id_by_org: dict[str, str] = {}
    insert_card = sa.text(
        "INSERT INTO project_finance_rate_cards "
        "(id, tenant_id, organization_id, project_id, name, card_kind, version, is_active, "
        "created_at, updated_at) "
        "VALUES (:id, :tenant_id, :organization_id, NULL, 'Legacy Resource Rates', 'legacy', "
        "1, true, :created_at, :updated_at)"
    )
    insert_line = sa.text(
        "INSERT INTO project_finance_rate_card_lines "
        "(id, tenant_id, organization_id, rate_card_id, rate_type, origin, resource_id, "
        "unit, rate_amount, rate_currency, effective_from, is_active, version, "
        "created_at, updated_at) "
        "VALUES (:id, :tenant_id, :organization_id, :rate_card_id, 'cost', 'legacy_seeded', "
        ":resource_id, 'HOUR', :rate_amount, :rate_currency, :effective_from, true, 1, "
        ":created_at, :updated_at)"
    )
    for resource in resources:
        org_key = f"{resource['tenant_id']}::{resource['organization_id']}"
        if org_key not in card_id_by_org:
            card_id = f"pfrc_legacy_{resource['organization_id']}"
            card_id_by_org[org_key] = card_id
            bind.execute(
                insert_card,
                {
                    "id": card_id,
                    "tenant_id": resource["tenant_id"],
                    "organization_id": resource["organization_id"],
                    "created_at": now,
                    "updated_at": now,
                },
            )
        resource_currency = str(resource["currency_code"] or "").strip().upper()
        organization_currency = str(resource["base_currency"] or "").strip().upper()
        resolved_currency = (
            resource_currency
            if resource_currency in _SUPPORTED_CURRENCY_CODES
            else organization_currency
        )
        if resolved_currency not in _SUPPORTED_CURRENCY_CODES:
            raise RuntimeError(
                "Cannot backfill legacy rate line for resource "
                f"'{resource['id']}'. Repair its Organization base currency first."
            )
        bind.execute(
            insert_line,
            {
                "id": f"pfrcl_legacy_{resource['id']}",
                "tenant_id": resource["tenant_id"],
                "organization_id": resource["organization_id"],
                "rate_card_id": card_id_by_org[org_key],
                "resource_id": resource["id"],
                "rate_amount": resource["hourly_rate"] or 0,
                "rate_currency": resolved_currency,
                "effective_from": LEGACY_RATE_BACKFILL_EFFECTIVE_FROM,
                "created_at": now,
                "updated_at": now,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("resources") as batch_op:
        batch_op.add_column(sa.Column("department_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_resources_department",
            "departments",
            ["department_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("idx_resources_department", "resources", ["department_id"])

    op.create_table(
        "project_finance_rate_cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("card_kind", sa.String(length=16), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_pf_rate_cards_version"),
        sa.CheckConstraint(
            "card_kind IS NULL OR card_kind = 'legacy'",
            name="ck_pf_rate_cards_card_kind",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_rate_cards_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_rate_cards_scoped_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_rate_cards_scoped_project",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_rate_cards_scoped_id",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_rate_cards_scope",
        "project_finance_rate_cards",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_rate_cards_project",
        "project_finance_rate_cards",
        ["project_id"],
    )
    op.create_index(
        "uq_pf_rate_cards_legacy_per_org",
        "project_finance_rate_cards",
        ["tenant_id", "organization_id"],
        unique=True,
        sqlite_where=sa.text("card_kind = 'legacy'"),
        postgresql_where=sa.text("card_kind = 'legacy'"),
    )

    op.create_table(
        "project_finance_rate_card_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("rate_card_id", sa.String(), nullable=False),
        sa.Column("rate_type", sa.String(length=16), nullable=False),
        sa.Column(
            "origin", sa.String(length=24), nullable=False, server_default="configured"
        ),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("customer_party_id", sa.String(), nullable=True),
        sa.Column("contract_reference", sa.String(length=128), nullable=True),
        sa.Column("role", sa.String(length=128), nullable=True),
        sa.Column("skill_code", sa.String(length=64), nullable=True),
        sa.Column("department_id", sa.String(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("rate_amount", sa.Numeric(19, 8, asdecimal=True), nullable=False),
        sa.Column("rate_currency", sa.String(length=8), nullable=False),
        sa.Column("overtime_multiplier", sa.Numeric(19, 8, asdecimal=True), nullable=True),
        sa.Column("weekend_multiplier", sa.Numeric(19, 8, asdecimal=True), nullable=True),
        sa.Column("holiday_multiplier", sa.Numeric(19, 8, asdecimal=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rate_type IN ('cost', 'billing')",
            name="ck_pf_rate_card_lines_rate_type",
        ),
        sa.CheckConstraint(
            "origin IN ('configured', 'legacy_seeded')",
            name="ck_pf_rate_card_lines_origin",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_pf_rate_card_lines_effective_range",
        ),
        sa.CheckConstraint(
            "(customer_party_id IS NULL AND contract_reference IS NULL) OR "
            "(customer_party_id IS NOT NULL AND contract_reference IS NOT NULL)",
            name="ck_pf_rate_card_lines_customer_contract",
        ),
        sa.CheckConstraint(
            "NOT (resource_id IS NOT NULL AND "
            "(role IS NOT NULL OR skill_code IS NOT NULL OR department_id IS NOT NULL))",
            name="ck_pf_rate_card_lines_selection_key_exclusive",
        ),
        sa.CheckConstraint(
            "resource_id IS NOT NULL OR role IS NOT NULL OR skill_code IS NOT NULL "
            "OR department_id IS NOT NULL",
            name="ck_pf_rate_card_lines_selection_key_required",
        ),
        sa.CheckConstraint("rate_amount >= 0", name="ck_pf_rate_card_lines_rate_amount"),
        sa.CheckConstraint("version >= 1", name="ck_pf_rate_card_lines_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_rate_card_lines_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "rate_card_id"],
            [
                "project_finance_rate_cards.tenant_id",
                "project_finance_rate_cards.organization_id",
                "project_finance_rate_cards.id",
            ],
            name="fk_pf_rate_card_lines_scoped_card",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_rate_card_lines_scope",
        "project_finance_rate_card_lines",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_rate_card_lines_card",
        "project_finance_rate_card_lines",
        ["rate_card_id"],
    )
    op.create_index(
        "idx_pf_rate_card_lines_resource",
        "project_finance_rate_card_lines",
        ["resource_id"],
    )
    op.create_index(
        "idx_pf_rate_card_lines_role_skill_dept",
        "project_finance_rate_card_lines",
        ["role", "skill_code", "department_id"],
    )

    _backfill_legacy_rate_lines(bind)

    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)

    op.drop_index(
        "idx_pf_rate_card_lines_role_skill_dept",
        table_name="project_finance_rate_card_lines",
    )
    op.drop_index(
        "idx_pf_rate_card_lines_resource", table_name="project_finance_rate_card_lines"
    )
    op.drop_index("idx_pf_rate_card_lines_card", table_name="project_finance_rate_card_lines")
    op.drop_index(
        "idx_pf_rate_card_lines_scope", table_name="project_finance_rate_card_lines"
    )
    op.drop_table("project_finance_rate_card_lines")

    op.drop_index(
        "uq_pf_rate_cards_legacy_per_org", table_name="project_finance_rate_cards"
    )
    op.drop_index("idx_pf_rate_cards_project", table_name="project_finance_rate_cards")
    op.drop_index("idx_pf_rate_cards_scope", table_name="project_finance_rate_cards")
    op.drop_table("project_finance_rate_cards")

    op.drop_index("idx_resources_department", table_name="resources")
    with op.batch_alter_table("resources") as batch_op:
        batch_op.drop_constraint("fk_resources_department", type_="foreignkey")
        batch_op.drop_column("department_id")


__all__ = ["downgrade", "upgrade"]
