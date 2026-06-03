"""Add platform enterprise calendars and PM calendar assignments.

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "n7o8p9q0r1s2"
down_revision = "m6n7o8p9q0r1"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_table_if_exists(table_name: str) -> None:
    if _table_exists(table_name):
        op.drop_table(table_name)


def upgrade() -> None:
    if not _table_exists("platform_calendars"):
        op.create_table(
            "platform_calendars",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("calendar_type", sa.String(length=64), nullable=False),
            sa.Column("base_calendar_id", sa.String(), nullable=True),
            sa.Column("scope_type", sa.String(length=64), nullable=True),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("timezone", sa.String(length=128), nullable=False, server_default="UTC"),
            sa.Column("locale", sa.String(length=32), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["base_calendar_id"],
                ["platform_calendars.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "code",
                name="ux_platform_calendars_org_code",
            ),
        )
    _create_index_if_missing("idx_platform_calendars_org", "platform_calendars", ["organization_id"])
    _create_index_if_missing("idx_platform_calendars_type", "platform_calendars", ["calendar_type"])
    _create_index_if_missing(
        "idx_platform_calendars_scope",
        "platform_calendars",
        ["scope_type", "scope_id"],
    )
    _create_index_if_missing(
        "idx_platform_calendars_active",
        "platform_calendars",
        ["organization_id", "is_active"],
    )

    if not _table_exists("calendar_working_rules"):
        op.create_table(
            "calendar_working_rules",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("weekday", sa.Integer(), nullable=False),
            sa.Column("is_working_day", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("start_time", sa.Time(), nullable=True),
            sa.Column("end_time", sa.Time(), nullable=True),
            sa.Column("break_start_time", sa.Time(), nullable=True),
            sa.Column("break_end_time", sa.Time(), nullable=True),
            sa.Column("break_minutes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hours_override", sa.Float(), nullable=True),
            sa.Column("shift_code", sa.String(length=64), nullable=True),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("calendar_id", "weekday", name="ux_cal_working_rules_cal_day"),
        )
    _create_index_if_missing("idx_cal_working_rules_calendar", "calendar_working_rules", ["calendar_id"])

    if not _table_exists("calendar_exceptions"):
        op.create_table(
            "calendar_exceptions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("scope_type", sa.String(length=64), nullable=True),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("exception_date", sa.Date(), nullable=False),
            sa.Column("exception_type", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("start_time", sa.Time(), nullable=True),
            sa.Column("end_time", sa.Time(), nullable=True),
            sa.Column("hours_override", sa.Float(), nullable=True),
            sa.Column("impact_type", sa.String(length=64), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "approval_status",
                sa.String(length=32),
                nullable=False,
                server_default="APPROVED",
            ),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_cal_exceptions_calendar", "calendar_exceptions", ["calendar_id"])
    _create_index_if_missing("idx_cal_exceptions_date", "calendar_exceptions", ["exception_date"])
    _create_index_if_missing("idx_cal_exceptions_scope", "calendar_exceptions", ["scope_type", "scope_id"])
    _create_index_if_missing(
        "idx_cal_exceptions_cal_date",
        "calendar_exceptions",
        ["calendar_id", "exception_date"],
    )

    if not _table_exists("calendar_recurring_events"):
        op.create_table(
            "calendar_recurring_events",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("scope_type", sa.String(length=64), nullable=True),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(length=256), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("recurrence_rule", sa.String(length=512), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("impact_type", sa.String(length=64), nullable=False),
            sa.Column("capacity_impact_percent", sa.Float(), nullable=True),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_cal_recurring_calendar", "calendar_recurring_events", ["calendar_id"])
    _create_index_if_missing("idx_cal_recurring_scope", "calendar_recurring_events", ["scope_type", "scope_id"])
    _create_index_if_missing("idx_cal_recurring_active", "calendar_recurring_events", ["is_active"])

    if not _table_exists("shift_patterns"):
        op.create_table(
            "shift_patterns",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("pattern_type", sa.String(length=64), nullable=False),
            sa.Column("rotation_cycle_days", sa.Integer(), nullable=True),
            sa.Column("timezone", sa.String(length=128), nullable=False, server_default="UTC"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "code", name="ux_shift_patterns_org_code"),
        )
    _create_index_if_missing("idx_shift_patterns_org", "shift_patterns", ["organization_id"])
    _create_index_if_missing("idx_shift_patterns_active", "shift_patterns", ["organization_id", "is_active"])

    if not _table_exists("shift_pattern_days"):
        op.create_table(
            "shift_pattern_days",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("shift_pattern_id", sa.String(), nullable=False),
            sa.Column("day_offset", sa.Integer(), nullable=False),
            sa.Column("is_working_day", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("start_time", sa.Time(), nullable=True),
            sa.Column("end_time", sa.Time(), nullable=True),
            sa.Column("break_minutes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hours", sa.Float(), nullable=True),
            sa.Column("shift_label", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(["shift_pattern_id"], ["shift_patterns.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("shift_pattern_id", "day_offset", name="ux_shift_pattern_days_offset"),
        )
    _create_index_if_missing("idx_shift_pattern_days_pattern", "shift_pattern_days", ["shift_pattern_id"])

    if not _table_exists("site_calendar_assignments"):
        op.create_table(
            "site_calendar_assignments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_site_cal_assign_site", "site_calendar_assignments", ["site_id"])
    _create_index_if_missing("idx_site_cal_assign_cal", "site_calendar_assignments", ["calendar_id"])

    if not _table_exists("department_calendar_assignments"):
        op.create_table(
            "department_calendar_assignments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("department_id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_dept_cal_assign_dept", "department_calendar_assignments", ["department_id"])
    _create_index_if_missing("idx_dept_cal_assign_cal", "department_calendar_assignments", ["calendar_id"])

    if not _table_exists("employee_calendar_assignments"):
        op.create_table(
            "employee_calendar_assignments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("employee_id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_emp_cal_assign_emp", "employee_calendar_assignments", ["employee_id"])
    _create_index_if_missing("idx_emp_cal_assign_cal", "employee_calendar_assignments", ["calendar_id"])

    if not _table_exists("project_calendar_assignments"):
        op.create_table(
            "project_calendar_assignments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_proj_cal_assign_project", "project_calendar_assignments", ["project_id"])
    _create_index_if_missing("idx_proj_cal_assign_cal", "project_calendar_assignments", ["calendar_id"])

    if not _table_exists("resource_calendar_assignments"):
        op.create_table(
            "resource_calendar_assignments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("resource_id", sa.String(), nullable=False),
            sa.Column("calendar_id", sa.String(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["calendar_id"], ["platform_calendars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("idx_res_cal_assign_resource", "resource_calendar_assignments", ["resource_id"])
    _create_index_if_missing("idx_res_cal_assign_cal", "resource_calendar_assignments", ["calendar_id"])


def downgrade() -> None:
    _drop_index_if_exists("idx_res_cal_assign_cal", "resource_calendar_assignments")
    _drop_index_if_exists("idx_res_cal_assign_resource", "resource_calendar_assignments")
    _drop_table_if_exists("resource_calendar_assignments")

    _drop_index_if_exists("idx_proj_cal_assign_cal", "project_calendar_assignments")
    _drop_index_if_exists("idx_proj_cal_assign_project", "project_calendar_assignments")
    _drop_table_if_exists("project_calendar_assignments")

    _drop_index_if_exists("idx_emp_cal_assign_cal", "employee_calendar_assignments")
    _drop_index_if_exists("idx_emp_cal_assign_emp", "employee_calendar_assignments")
    _drop_table_if_exists("employee_calendar_assignments")

    _drop_index_if_exists("idx_dept_cal_assign_cal", "department_calendar_assignments")
    _drop_index_if_exists("idx_dept_cal_assign_dept", "department_calendar_assignments")
    _drop_table_if_exists("department_calendar_assignments")

    _drop_index_if_exists("idx_site_cal_assign_cal", "site_calendar_assignments")
    _drop_index_if_exists("idx_site_cal_assign_site", "site_calendar_assignments")
    _drop_table_if_exists("site_calendar_assignments")

    _drop_index_if_exists("idx_shift_pattern_days_pattern", "shift_pattern_days")
    _drop_table_if_exists("shift_pattern_days")

    _drop_index_if_exists("idx_shift_patterns_active", "shift_patterns")
    _drop_index_if_exists("idx_shift_patterns_org", "shift_patterns")
    _drop_table_if_exists("shift_patterns")

    _drop_index_if_exists("idx_cal_recurring_active", "calendar_recurring_events")
    _drop_index_if_exists("idx_cal_recurring_scope", "calendar_recurring_events")
    _drop_index_if_exists("idx_cal_recurring_calendar", "calendar_recurring_events")
    _drop_table_if_exists("calendar_recurring_events")

    _drop_index_if_exists("idx_cal_exceptions_cal_date", "calendar_exceptions")
    _drop_index_if_exists("idx_cal_exceptions_scope", "calendar_exceptions")
    _drop_index_if_exists("idx_cal_exceptions_date", "calendar_exceptions")
    _drop_index_if_exists("idx_cal_exceptions_calendar", "calendar_exceptions")
    _drop_table_if_exists("calendar_exceptions")

    _drop_index_if_exists("idx_cal_working_rules_calendar", "calendar_working_rules")
    _drop_table_if_exists("calendar_working_rules")

    _drop_index_if_exists("idx_platform_calendars_active", "platform_calendars")
    _drop_index_if_exists("idx_platform_calendars_scope", "platform_calendars")
    _drop_index_if_exists("idx_platform_calendars_type", "platform_calendars")
    _drop_index_if_exists("idx_platform_calendars_org", "platform_calendars")
    _drop_table_if_exists("platform_calendars")
