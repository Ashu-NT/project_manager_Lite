"""add canonical project finance configuration

Revision ID: j8k9l0m1n2o3
Revises: i7j8k9l0m1n2
Create Date: 2026-08-02
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "j8k9l0m1n2o3"
down_revision = "i7j8k9l0m1n2"
branch_labels = None
depends_on = None


_TABLES = (
    "project_finance_cost_codes",
    "project_finance_profiles",
    "project_finance_cost_code_restrictions",
)

# Frozen from ISO 4217 List One (2026-01-01), excluding codes without a
# defined minor unit because Project Finance requires deterministic rounding.
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


def _backfill_profiles(bind) -> None:
    projects = bind.execute(
        sa.text(
            "SELECT p.id, p.tenant_id, p.organization_id, p.currency, "
            "p.start_date, p.end_date, o.base_currency "
            "FROM projects p JOIN organizations o ON o.id = p.organization_id "
            "AND o.tenant_id = p.tenant_id "
            "WHERE p.tenant_id IS NOT NULL AND p.organization_id IS NOT NULL"
        )
    ).mappings()
    now = datetime.now(timezone.utc)
    insert_profile = sa.text(
        "INSERT INTO project_finance_profiles "
        "(id, tenant_id, organization_id, project_id, currency_code, status, "
        "billing_method, budget_control_mode, cost_code_policy, "
        "financial_start_date, financial_end_date, is_funded, is_billable, "
        "default_cost_code_id, version, created_at, updated_at) "
        "VALUES (:id, :tenant_id, :organization_id, :project_id, :currency_code, "
        "'active', 'non_billable', 'warn', 'all_active', :start_date, :end_date, "
        "false, false, NULL, 1, :created_at, :updated_at)"
    )
    for project in projects:
        project_currency = str(project["currency"] or "").strip().upper()
        organization_currency = str(project["base_currency"] or "").strip().upper()
        resolved_currency = (
            project_currency
            if project_currency in _SUPPORTED_CURRENCY_CODES
            else organization_currency
        )
        if resolved_currency not in _SUPPORTED_CURRENCY_CODES:
            raise RuntimeError(
                "Cannot backfill Project Financial Profile currency for project "
                f"'{project['id']}'. Repair its Organization base currency first."
            )
        bind.execute(
            insert_profile,
            {
                "id": f"pfp_{project['id']}",
                "tenant_id": project["tenant_id"],
                "organization_id": project["organization_id"],
                "project_id": project["id"],
                "currency_code": resolved_currency,
                "start_date": project["start_date"],
                "end_date": project["end_date"],
                "created_at": now,
                "updated_at": now,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("organizations") as batch_op:
        batch_op.create_unique_constraint(
            "uq_organizations_tenant_id",
            ["tenant_id", "id"],
        )
    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_unique_constraint(
            "uq_projects_tenant_organization_id",
            ["tenant_id", "organization_id", "id"],
        )

    op.create_table(
        "project_finance_cost_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("external_system", sa.String(length=64), nullable=True),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(code) >= 1 AND length(code) <= 64",
            name="ck_pf_cost_codes_code_length",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_pf_cost_codes_effective_range",
        ),
        sa.CheckConstraint(
            "(external_system IS NULL AND external_reference IS NULL) OR "
            "(external_system IS NOT NULL AND external_reference IS NOT NULL)",
            name="ck_pf_cost_codes_external_mapping",
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_pf_cost_codes_parent_not_self",
        ),
        sa.CheckConstraint("version >= 1", name="ck_pf_cost_codes_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_cost_codes_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_cost_codes_scoped_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "parent_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_cost_codes_scoped_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_cost_codes_scoped_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "code",
            name="uq_pf_cost_codes_scoped_code",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_cost_codes_scope",
        "project_finance_cost_codes",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_cost_codes_parent",
        "project_finance_cost_codes",
        ["parent_id"],
    )
    op.create_index(
        "idx_pf_cost_codes_active",
        "project_finance_cost_codes",
        ["is_active"],
    )

    op.create_table(
        "project_finance_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column(
            "billing_method",
            sa.String(length=32),
            nullable=False,
            server_default="non_billable",
        ),
        sa.Column(
            "budget_control_mode",
            sa.String(length=16),
            nullable=False,
            server_default="warn",
        ),
        sa.Column(
            "cost_code_policy",
            sa.String(length=16),
            nullable=False,
            server_default="all_active",
        ),
        sa.Column("financial_start_date", sa.Date(), nullable=True),
        sa.Column("financial_end_date", sa.Date(), nullable=True),
        sa.Column("is_funded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_billable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_cost_code_id", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'on_hold', 'closed')",
            name="ck_pf_profiles_status",
        ),
        sa.CheckConstraint(
            "billing_method IN ('non_billable', 'time_and_materials', 'fixed_price', 'cost_plus')",
            name="ck_pf_profiles_billing_method",
        ),
        sa.CheckConstraint(
            "budget_control_mode IN ('none', 'warn', 'block')",
            name="ck_pf_profiles_budget_control_mode",
        ),
        sa.CheckConstraint(
            "cost_code_policy IN ('all_active', 'restricted')",
            name="ck_pf_profiles_cost_code_policy",
        ),
        sa.CheckConstraint(
            "financial_end_date IS NULL OR financial_start_date IS NULL OR "
            "financial_end_date >= financial_start_date",
            name="ck_pf_profiles_date_range",
        ),
        sa.CheckConstraint(
            "(is_billable = false AND billing_method = 'non_billable') OR "
            "(is_billable = true AND billing_method <> 'non_billable')",
            name="ck_pf_profiles_billing_policy",
        ),
        sa.CheckConstraint("version >= 1", name="ck_pf_profiles_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_profiles_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_profiles_scoped_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "default_cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_profiles_scoped_default_cost_code",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            name="uq_pf_profiles_scoped_project",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_profiles_scope",
        "project_finance_profiles",
        ["tenant_id", "organization_id"],
    )

    op.create_table(
        "project_finance_cost_code_restrictions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_restrictions_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_restrictions_scoped_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_restrictions_scoped_cost_code",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "cost_code_id",
            name="uq_pf_restrictions_project_cost_code",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_restrictions_project",
        "project_finance_cost_code_restrictions",
        ["tenant_id", "organization_id", "project_id"],
    )

    _backfill_profiles(bind)

    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)

    op.drop_index(
        "idx_pf_restrictions_project",
        table_name="project_finance_cost_code_restrictions",
    )
    op.drop_table("project_finance_cost_code_restrictions")
    op.drop_index("idx_pf_profiles_scope", table_name="project_finance_profiles")
    op.drop_table("project_finance_profiles")
    op.drop_index("idx_pf_cost_codes_active", table_name="project_finance_cost_codes")
    op.drop_index("idx_pf_cost_codes_parent", table_name="project_finance_cost_codes")
    op.drop_index("idx_pf_cost_codes_scope", table_name="project_finance_cost_codes")
    op.drop_table("project_finance_cost_codes")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint(
            "uq_projects_tenant_organization_id",
            type_="unique",
        )
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_constraint("uq_organizations_tenant_id", type_="unique")


__all__ = ["downgrade", "upgrade"]
