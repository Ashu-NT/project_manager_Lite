"""PM enterprise upgrade: constraints, baseline governance, cost commitment, skills

Adds the domain fields introduced by PM modernization steps 3, 7, 8, and 4:
  - tasks: constraint_type, constraint_date
  - project_baselines: status lifecycle fields + indexes
  - baseline_variance_records: new table
  - cost_items: forecast_amount, commitment_status, vendor_reference
  - resource_skills, resource_certifications, task_skill_requirements: new tables

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6, b18e7b3f21c4
Create Date: 2026-05-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "i2j3k4l5m6n7"
down_revision = ("h1i2j3k4l5m6", "b18e7b3f21c4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 3: scheduling constraints on tasks ──────────────────────────────
    op.add_column("tasks", sa.Column("constraint_type", sa.String(length=32), nullable=True))
    op.add_column("tasks", sa.Column("constraint_date", sa.Date(), nullable=True))
    op.create_index("idx_tasks_constraint_type", "tasks", ["constraint_type"], unique=False)

    # ── Step 7: baseline governance lifecycle fields ─────────────────────────
    op.add_column(
        "project_baselines",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
    )
    op.add_column("project_baselines", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("project_baselines", sa.Column("submitted_by", sa.String(), nullable=True))
    op.add_column("project_baselines", sa.Column("submitted_at", sa.Date(), nullable=True))
    op.add_column("project_baselines", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column("project_baselines", sa.Column("approved_at", sa.Date(), nullable=True))
    op.add_column("project_baselines", sa.Column("notes", sa.String(), nullable=True))

    op.create_index("idx_baseline_status", "project_baselines", ["status"], unique=False)
    op.create_index(
        "idx_baseline_project_status",
        "project_baselines",
        ["project_id", "status"],
        unique=False,
    )

    # ── Step 7: baseline variance records table ───────────────────────────────
    op.create_table(
        "baseline_variance_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("new_baseline_id", sa.String(), nullable=False),
        sa.Column("superseded_baseline_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("task_name", sa.String(), nullable=True),
        sa.Column("start_variance_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finish_variance_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_variance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["new_baseline_id"], ["project_baselines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["superseded_baseline_id"], ["project_baselines.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_variance_new_baseline",
        "baseline_variance_records",
        ["new_baseline_id"],
        unique=False,
    )
    op.create_index(
        "idx_variance_superseded",
        "baseline_variance_records",
        ["superseded_baseline_id"],
        unique=False,
    )
    op.create_index(
        "idx_variance_project",
        "baseline_variance_records",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "idx_variance_task",
        "baseline_variance_records",
        ["task_id"],
        unique=False,
    )

    # ── Step 8: cost commitment lifecycle fields ──────────────────────────────
    op.add_column("cost_items", sa.Column("forecast_amount", sa.Float(), nullable=True))
    op.add_column(
        "cost_items",
        sa.Column(
            "commitment_status",
            sa.String(length=20),
            nullable=False,
            server_default="uncommitted",
        ),
    )
    op.add_column("cost_items", sa.Column("vendor_reference", sa.String(), nullable=True))

    op.create_index(
        "idx_costs_commitment_status",
        "cost_items",
        ["commitment_status"],
        unique=False,
    )

    # ── Step 4: resource skills ───────────────────────────────────────────────
    op.create_table(
        "resource_skills",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("skill_code", sa.String(), nullable=False),
        sa.Column("skill_name", sa.String(), nullable=False),
        sa.Column("proficiency", sa.String(length=20), nullable=False, server_default="intermediate"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_skills_resource", "resource_skills", ["resource_id"], unique=False)
    op.create_index("idx_skills_code", "resource_skills", ["skill_code"], unique=False)
    op.create_index(
        "ux_resource_skill_code",
        "resource_skills",
        ["resource_id", "skill_code"],
        unique=True,
    )

    # ── Step 4: resource certifications ──────────────────────────────────────
    op.create_table(
        "resource_certifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("certification_code", sa.String(), nullable=False),
        sa.Column("certification_name", sa.String(), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("issuing_authority", sa.String(), nullable=True),
        sa.Column("certificate_number", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_certs_resource", "resource_certifications", ["resource_id"], unique=False)
    op.create_index("idx_certs_code", "resource_certifications", ["certification_code"], unique=False)
    op.create_index("idx_certs_expiry", "resource_certifications", ["expiry_date"], unique=False)

    # ── Step 4: task skill requirements ──────────────────────────────────────
    op.create_table(
        "task_skill_requirements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("skill_code", sa.String(), nullable=True),
        sa.Column("certification_code", sa.String(), nullable=True),
        sa.Column("required_proficiency", sa.String(length=20), nullable=True),
        sa.Column(
            "validation_mode",
            sa.String(length=10),
            nullable=False,
            server_default="warn",
        ),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_skill_req_task", "task_skill_requirements", ["task_id"], unique=False)
    op.create_index("idx_skill_req_code", "task_skill_requirements", ["skill_code"], unique=False)
    op.create_index(
        "idx_cert_req_code",
        "task_skill_requirements",
        ["certification_code"],
        unique=False,
    )


def downgrade() -> None:
    # task_skill_requirements
    op.drop_index("idx_cert_req_code", table_name="task_skill_requirements")
    op.drop_index("idx_skill_req_code", table_name="task_skill_requirements")
    op.drop_index("idx_skill_req_task", table_name="task_skill_requirements")
    op.drop_table("task_skill_requirements")

    # resource_certifications
    op.drop_index("idx_certs_expiry", table_name="resource_certifications")
    op.drop_index("idx_certs_code", table_name="resource_certifications")
    op.drop_index("idx_certs_resource", table_name="resource_certifications")
    op.drop_table("resource_certifications")

    # resource_skills
    op.drop_index("ux_resource_skill_code", table_name="resource_skills")
    op.drop_index("idx_skills_code", table_name="resource_skills")
    op.drop_index("idx_skills_resource", table_name="resource_skills")
    op.drop_table("resource_skills")

    # cost_items
    op.drop_index("idx_costs_commitment_status", table_name="cost_items")
    op.drop_column("cost_items", "vendor_reference")
    op.drop_column("cost_items", "commitment_status")
    op.drop_column("cost_items", "forecast_amount")

    # baseline_variance_records
    op.drop_index("idx_variance_task", table_name="baseline_variance_records")
    op.drop_index("idx_variance_project", table_name="baseline_variance_records")
    op.drop_index("idx_variance_superseded", table_name="baseline_variance_records")
    op.drop_index("idx_variance_new_baseline", table_name="baseline_variance_records")
    op.drop_table("baseline_variance_records")

    # project_baselines
    op.drop_index("idx_baseline_project_status", table_name="project_baselines")
    op.drop_index("idx_baseline_status", table_name="project_baselines")
    op.drop_column("project_baselines", "notes")
    op.drop_column("project_baselines", "approved_at")
    op.drop_column("project_baselines", "approved_by")
    op.drop_column("project_baselines", "submitted_at")
    op.drop_column("project_baselines", "submitted_by")
    op.drop_column("project_baselines", "version")
    op.drop_column("project_baselines", "status")

    # tasks
    op.drop_index("idx_tasks_constraint_type", table_name="tasks")
    op.drop_column("tasks", "constraint_date")
    op.drop_column("tasks", "constraint_type")
