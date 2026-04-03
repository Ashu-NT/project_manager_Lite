"""add maintenance work request and work order tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
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
    # Create maintenance_work_requests table
    if not _has_table("maintenance_work_requests"):
        op.create_table(
            "maintenance_work_requests",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("work_request_code", sa.String(length=64), nullable=False),
            sa.Column("source_type", sa.String(length=16), nullable=False),
            sa.Column("request_type", sa.String(length=64), nullable=False),
            sa.Column("asset_id", sa.String(), nullable=True),
            sa.Column("component_id", sa.String(), nullable=True),
            sa.Column("system_id", sa.String(), nullable=True),
            sa.Column("location_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(length=256), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("priority", sa.String(length=8), nullable=False, server_default="MEDIUM"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="NEW"),
            sa.Column("requested_at", sa.DateTime(), nullable=True),
            sa.Column("requested_by_user_id", sa.String(), nullable=True),
            sa.Column("requested_by_name_snapshot", sa.String(length=256), nullable=False, server_default=""),
            sa.Column("triaged_at", sa.DateTime(), nullable=True),
            sa.Column("triaged_by_user_id", sa.String(), nullable=True),
            sa.Column("failure_symptom_code", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("safety_risk_level", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("production_impact_level", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_work_requests_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["site_id"],
                ["sites.id"],
                name="fk_maintenance_work_requests_site_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["asset_id"],
                ["maintenance_assets.id"],
                name="fk_maintenance_work_requests_asset_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["component_id"],
                ["maintenance_asset_components.id"],
                name="fk_maintenance_work_requests_component_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["system_id"],
                ["maintenance_systems.id"],
                name="fk_maintenance_work_requests_system_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["location_id"],
                ["maintenance_locations.id"],
                name="fk_maintenance_work_requests_location_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["requested_by_user_id"],
                ["users.id"],
                name="fk_maintenance_work_requests_requested_by_user_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["triaged_by_user_id"],
                ["users.id"],
                name="fk_maintenance_work_requests_triaged_by_user_id",
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("organization_id", "work_request_code", name="ux_maintenance_work_requests_org_code"),
        )

    # Create maintenance_work_orders table
    if not _has_table("maintenance_work_orders"):
        op.create_table(
            "maintenance_work_orders",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("work_order_code", sa.String(length=64), nullable=False),
            sa.Column("work_order_type", sa.String(length=16), nullable=False),
            sa.Column("source_type", sa.String(length=64), nullable=False),
            sa.Column("source_id", sa.String(), nullable=True),
            sa.Column("asset_id", sa.String(), nullable=True),
            sa.Column("component_id", sa.String(), nullable=True),
            sa.Column("system_id", sa.String(), nullable=True),
            sa.Column("location_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(length=256), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("priority", sa.String(length=8), nullable=False, server_default="MEDIUM"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="DRAFT"),
            sa.Column("requested_by_user_id", sa.String(), nullable=True),
            sa.Column("planner_user_id", sa.String(), nullable=True),
            sa.Column("supervisor_user_id", sa.String(), nullable=True),
            sa.Column("assigned_team_id", sa.String(), nullable=True),
            sa.Column("assigned_employee_id", sa.String(), nullable=True),
            sa.Column("planned_start", sa.DateTime(), nullable=True),
            sa.Column("planned_end", sa.DateTime(), nullable=True),
            sa.Column("actual_start", sa.DateTime(), nullable=True),
            sa.Column("actual_end", sa.DateTime(), nullable=True),
            sa.Column("requires_shutdown", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("permit_required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("failure_code", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("root_cause_code", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("downtime_minutes", sa.Integer(), nullable=True),
            sa.Column("parts_cost", sa.Numeric(18, 2), nullable=True),
            sa.Column("labor_cost", sa.Numeric(18, 2), nullable=True),
            sa.Column("vendor_party_id", sa.String(), nullable=True),
            sa.Column("is_preventive", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by_user_id", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_work_orders_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["site_id"],
                ["sites.id"],
                name="fk_maintenance_work_orders_site_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["asset_id"],
                ["maintenance_assets.id"],
                name="fk_maintenance_work_orders_asset_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["component_id"],
                ["maintenance_asset_components.id"],
                name="fk_maintenance_work_orders_component_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["system_id"],
                ["maintenance_systems.id"],
                name="fk_maintenance_work_orders_system_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["location_id"],
                ["maintenance_locations.id"],
                name="fk_maintenance_work_orders_location_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["requested_by_user_id"],
                ["users.id"],
                name="fk_maintenance_work_orders_requested_by_user_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["planner_user_id"],
                ["users.id"],
                name="fk_maintenance_work_orders_planner_user_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["supervisor_user_id"],
                ["users.id"],
                name="fk_maintenance_work_orders_supervisor_user_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["assigned_employee_id"],
                ["employees.id"],
                name="fk_maintenance_work_orders_assigned_employee_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["vendor_party_id"],
                ["parties.id"],
                name="fk_maintenance_work_orders_vendor_party_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["closed_by_user_id"],
                ["users.id"],
                name="fk_maintenance_work_orders_closed_by_user_id",
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("organization_id", "work_order_code", name="ux_maintenance_work_orders_org_code"),
        )

    # Create indexes for maintenance_work_requests
    for index_name, columns in (
        ("idx_maintenance_work_requests_org", ["organization_id"]),
        ("idx_maintenance_work_requests_site", ["site_id"]),
        ("idx_maintenance_work_requests_asset", ["asset_id"]),
        ("idx_maintenance_work_requests_component", ["component_id"]),
        ("idx_maintenance_work_requests_system", ["system_id"]),
        ("idx_maintenance_work_requests_location", ["location_id"]),
        ("idx_maintenance_work_requests_status", ["status"]),
        ("idx_maintenance_work_requests_priority", ["priority"]),
        ("idx_maintenance_work_requests_requested_by", ["requested_by_user_id"]),
        ("idx_maintenance_work_requests_triaged_by", ["triaged_by_user_id"]),
    ):
        if not _has_index("maintenance_work_requests", index_name):
            op.create_index(index_name, "maintenance_work_requests", columns, unique=False)

    # Create indexes for maintenance_work_orders
    for index_name, columns in (
        ("idx_maintenance_work_orders_org", ["organization_id"]),
        ("idx_maintenance_work_orders_site", ["site_id"]),
        ("idx_maintenance_work_orders_asset", ["asset_id"]),
        ("idx_maintenance_work_orders_component", ["component_id"]),
        ("idx_maintenance_work_orders_system", ["system_id"]),
        ("idx_maintenance_work_orders_location", ["location_id"]),
        ("idx_maintenance_work_orders_status", ["status"]),
        ("idx_maintenance_work_orders_priority", ["priority"]),
        ("idx_maintenance_work_orders_assigned_team", ["assigned_team_id"]),
        ("idx_maintenance_work_orders_assigned_employee", ["assigned_employee_id"]),
        ("idx_maintenance_work_orders_planner", ["planner_user_id"]),
        ("idx_maintenance_work_orders_supervisor", ["supervisor_user_id"]),
        ("idx_maintenance_work_orders_type", ["work_order_type"]),
        ("idx_maintenance_work_orders_preventive", ["is_preventive"]),
        ("idx_maintenance_work_orders_emergency", ["is_emergency"]),
    ):
        if not _has_index("maintenance_work_orders", index_name):
            op.create_index(index_name, "maintenance_work_orders", columns, unique=False)


def downgrade() -> None:
    # Drop maintenance_work_orders table
    if _has_table("maintenance_work_orders"):
        for index_name in (
            "idx_maintenance_work_orders_emergency",
            "idx_maintenance_work_orders_preventive",
            "idx_maintenance_work_orders_type",
            "idx_maintenance_work_orders_supervisor",
            "idx_maintenance_work_orders_planner",
            "idx_maintenance_work_orders_assigned_employee",
            "idx_maintenance_work_orders_assigned_team",
            "idx_maintenance_work_orders_priority",
            "idx_maintenance_work_orders_status",
            "idx_maintenance_work_orders_location",
            "idx_maintenance_work_orders_system",
            "idx_maintenance_work_orders_component",
            "idx_maintenance_work_orders_asset",
            "idx_maintenance_work_orders_site",
            "idx_maintenance_work_orders_org",
        ):
            if _has_index("maintenance_work_orders", index_name):
                op.drop_index(index_name, table_name="maintenance_work_orders")
        op.drop_table("maintenance_work_orders")

    # Drop maintenance_work_requests table
    if _has_table("maintenance_work_requests"):
        for index_name in (
            "idx_maintenance_work_requests_triaged_by",
            "idx_maintenance_work_requests_requested_by",
            "idx_maintenance_work_requests_priority",
            "idx_maintenance_work_requests_status",
            "idx_maintenance_work_requests_location",
            "idx_maintenance_work_requests_system",
            "idx_maintenance_work_requests_component",
            "idx_maintenance_work_requests_asset",
            "idx_maintenance_work_requests_site",
            "idx_maintenance_work_requests_org",
        ):
            if _has_index("maintenance_work_requests", index_name):
                op.drop_index(index_name, table_name="maintenance_work_requests")
        op.drop_table("maintenance_work_requests")
