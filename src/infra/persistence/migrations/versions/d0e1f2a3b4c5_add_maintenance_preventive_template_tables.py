"""add maintenance preventive template tables

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-04-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("maintenance_task_templates"):
        op.create_table(
            "maintenance_task_templates",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("task_template_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("maintenance_type", sa.String(length=64), nullable=True),
            sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("template_status", sa.String(length=16), nullable=False, server_default="DRAFT"),
            sa.Column("estimated_minutes", sa.Integer(), nullable=True),
            sa.Column("required_skill", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("requires_shutdown", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("requires_permit", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "task_template_code", name="ux_maintenance_task_templates_org_code"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_task_templates_organization_id",
                ondelete="CASCADE",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_task_templates_org", ["organization_id"]),
        ("idx_maintenance_task_templates_status", ["template_status"]),
        ("idx_maintenance_task_templates_active", ["is_active"]),
        ("idx_maintenance_task_templates_type", ["maintenance_type"]),
    ):
        if not _has_index("maintenance_task_templates", index_name):
            op.create_index(index_name, "maintenance_task_templates", columns, unique=False)

    if not _has_table("maintenance_task_step_templates"):
        op.create_table(
            "maintenance_task_step_templates",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("task_template_id", sa.String(), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("instruction", sa.Text(), nullable=False),
            sa.Column("expected_result", sa.Text(), nullable=False, server_default=""),
            sa.Column("hint_level", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("hint_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("requires_measurement", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("requires_photo", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("measurement_unit", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "task_template_id",
                "step_number",
                name="ux_maintenance_task_step_templates_task_step_number",
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_task_step_templates_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["task_template_id"],
                ["maintenance_task_templates.id"],
                name="fk_maintenance_task_step_templates_task_template_id",
                ondelete="CASCADE",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_task_step_templates_org", ["organization_id"]),
        ("idx_maintenance_task_step_templates_task", ["task_template_id"]),
        ("idx_maintenance_task_step_templates_active", ["is_active"]),
        ("idx_maintenance_task_step_templates_sort", ["sort_order"]),
    ):
        if not _has_index("maintenance_task_step_templates", index_name):
            op.create_index(index_name, "maintenance_task_step_templates", columns, unique=False)

    if not _has_table("maintenance_preventive_plans"):
        op.create_table(
            "maintenance_preventive_plans",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("plan_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("asset_id", sa.String(), nullable=True),
            sa.Column("component_id", sa.String(), nullable=True),
            sa.Column("system_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="DRAFT"),
            sa.Column("plan_type", sa.String(length=24), nullable=False, server_default="PREVENTIVE"),
            sa.Column("priority", sa.String(length=16), nullable=False, server_default="MEDIUM"),
            sa.Column("trigger_mode", sa.String(length=16), nullable=False, server_default="CALENDAR"),
            sa.Column("calendar_frequency_unit", sa.String(length=16), nullable=True),
            sa.Column("calendar_frequency_value", sa.Integer(), nullable=True),
            sa.Column("sensor_id", sa.String(), nullable=True),
            sa.Column("sensor_threshold", sa.Numeric(18, 6), nullable=True),
            sa.Column("sensor_direction", sa.String(length=24), nullable=True),
            sa.Column("sensor_reset_rule", sa.Text(), nullable=False, server_default=""),
            sa.Column("last_generated_at", sa.DateTime(), nullable=True),
            sa.Column("last_completed_at", sa.DateTime(), nullable=True),
            sa.Column("next_due_at", sa.DateTime(), nullable=True),
            sa.Column("next_due_counter", sa.Numeric(18, 6), nullable=True),
            sa.Column("requires_shutdown", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("auto_generate_work_order", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "plan_code", name="ux_maintenance_preventive_plans_org_code"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_preventive_plans_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"], name="fk_maintenance_preventive_plans_site_id"),
            sa.ForeignKeyConstraint(
                ["asset_id"],
                ["maintenance_assets.id"],
                name="fk_maintenance_preventive_plans_asset_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["component_id"],
                ["maintenance_asset_components.id"],
                name="fk_maintenance_preventive_plans_component_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["system_id"],
                ["maintenance_systems.id"],
                name="fk_maintenance_preventive_plans_system_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["sensor_id"],
                ["maintenance_sensors.id"],
                name="fk_maintenance_preventive_plans_sensor_id",
                ondelete="SET NULL",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_preventive_plans_org", ["organization_id"]),
        ("idx_maintenance_preventive_plans_site", ["site_id"]),
        ("idx_maintenance_preventive_plans_asset", ["asset_id"]),
        ("idx_maintenance_preventive_plans_component", ["component_id"]),
        ("idx_maintenance_preventive_plans_system", ["system_id"]),
        ("idx_maintenance_preventive_plans_status", ["status"]),
        ("idx_maintenance_preventive_plans_type", ["plan_type"]),
        ("idx_maintenance_preventive_plans_trigger", ["trigger_mode"]),
        ("idx_maintenance_preventive_plans_sensor", ["sensor_id"]),
    ):
        if not _has_index("maintenance_preventive_plans", index_name):
            op.create_index(index_name, "maintenance_preventive_plans", columns, unique=False)

    if not _has_table("maintenance_preventive_plan_tasks"):
        op.create_table(
            "maintenance_preventive_plan_tasks",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("plan_id", sa.String(), nullable=False),
            sa.Column("task_template_id", sa.String(), nullable=False),
            sa.Column("trigger_scope", sa.String(length=16), nullable=False, server_default="INHERIT_PLAN"),
            sa.Column("trigger_mode_override", sa.String(length=16), nullable=True),
            sa.Column("calendar_frequency_unit_override", sa.String(length=16), nullable=True),
            sa.Column("calendar_frequency_value_override", sa.Integer(), nullable=True),
            sa.Column("sensor_id_override", sa.String(), nullable=True),
            sa.Column("sensor_threshold_override", sa.Numeric(18, 6), nullable=True),
            sa.Column("sensor_direction_override", sa.String(length=24), nullable=True),
            sa.Column("sequence_no", sa.Integer(), nullable=False),
            sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("default_assigned_employee_id", sa.String(), nullable=True),
            sa.Column("default_assigned_team_id", sa.String(), nullable=True),
            sa.Column("estimated_minutes_override", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "plan_id",
                "sequence_no",
                name="ux_maintenance_preventive_plan_tasks_plan_sequence",
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_plan_tasks_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["plan_id"],
                ["maintenance_preventive_plans.id"],
                name="fk_maintenance_plan_tasks_plan_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["task_template_id"],
                ["maintenance_task_templates.id"],
                name="fk_maintenance_plan_tasks_task_template_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["sensor_id_override"],
                ["maintenance_sensors.id"],
                name="fk_maintenance_plan_tasks_sensor_id_override",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["default_assigned_employee_id"],
                ["employees.id"],
                name="fk_maintenance_plan_tasks_default_employee_id",
                ondelete="SET NULL",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_plan_tasks_org", ["organization_id"]),
        ("idx_maintenance_plan_tasks_plan", ["plan_id"]),
        ("idx_maintenance_plan_tasks_template", ["task_template_id"]),
        ("idx_maintenance_plan_tasks_sensor", ["sensor_id_override"]),
        ("idx_maintenance_plan_tasks_assigned_employee", ["default_assigned_employee_id"]),
    ):
        if not _has_index("maintenance_preventive_plan_tasks", index_name):
            op.create_index(index_name, "maintenance_preventive_plan_tasks", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_preventive_plan_tasks"):
        for index_name in (
            "idx_maintenance_plan_tasks_assigned_employee",
            "idx_maintenance_plan_tasks_sensor",
            "idx_maintenance_plan_tasks_template",
            "idx_maintenance_plan_tasks_plan",
            "idx_maintenance_plan_tasks_org",
        ):
            if _has_index("maintenance_preventive_plan_tasks", index_name):
                op.drop_index(index_name, table_name="maintenance_preventive_plan_tasks")
        op.drop_table("maintenance_preventive_plan_tasks")

    if _has_table("maintenance_preventive_plans"):
        for index_name in (
            "idx_maintenance_preventive_plans_sensor",
            "idx_maintenance_preventive_plans_trigger",
            "idx_maintenance_preventive_plans_type",
            "idx_maintenance_preventive_plans_status",
            "idx_maintenance_preventive_plans_system",
            "idx_maintenance_preventive_plans_component",
            "idx_maintenance_preventive_plans_asset",
            "idx_maintenance_preventive_plans_site",
            "idx_maintenance_preventive_plans_org",
        ):
            if _has_index("maintenance_preventive_plans", index_name):
                op.drop_index(index_name, table_name="maintenance_preventive_plans")
        op.drop_table("maintenance_preventive_plans")

    if _has_table("maintenance_task_step_templates"):
        for index_name in (
            "idx_maintenance_task_step_templates_sort",
            "idx_maintenance_task_step_templates_active",
            "idx_maintenance_task_step_templates_task",
            "idx_maintenance_task_step_templates_org",
        ):
            if _has_index("maintenance_task_step_templates", index_name):
                op.drop_index(index_name, table_name="maintenance_task_step_templates")
        op.drop_table("maintenance_task_step_templates")

    if _has_table("maintenance_task_templates"):
        for index_name in (
            "idx_maintenance_task_templates_type",
            "idx_maintenance_task_templates_active",
            "idx_maintenance_task_templates_status",
            "idx_maintenance_task_templates_org",
        ):
            if _has_index("maintenance_task_templates", index_name):
                op.drop_index(index_name, table_name="maintenance_task_templates")
        op.drop_table("maintenance_task_templates")
