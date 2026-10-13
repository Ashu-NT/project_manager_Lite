"""Persist request-specific reviewer permission for governed Approval decisions."""

import sqlalchemy as sa
from alembic import op

revision = "b1d7c2f4a96e"
down_revision = "c9a73e6d41b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("approval_requests") as batch:
        batch.add_column(sa.Column(
            "decision_permission", sa.String(length=128), nullable=False,
            server_default="approval.decide",
        ))
    permissions = {
        "baseline.create": "baseline.approve",
        "dependency.add": "task.approve",
        "dependency.remove": "task.approve",
        "dependency.update": "task.approve",
        "task.constraint.update": "task.approve",
        "scheduling.leveling.apply": "task.approve",
        "budget.approve": "budget.approve",
        "forecast.approve": "forecast.approve",
        "project_cost.approve": "project_cost.approve",
        "financial_change.apply": "financial_change.approve",
        "project_billing_preparation.approve": "billing_preparation.approve",
    }
    for request_type, permission in permissions.items():
        op.execute(sa.text(
            "UPDATE approval_requests SET decision_permission = :permission "
            "WHERE request_type = :request_type"
        ).bindparams(permission=permission, request_type=request_type))
    with op.batch_alter_table("approval_requests") as batch:
        batch.alter_column("decision_permission", server_default=None)


def downgrade():
    with op.batch_alter_table("approval_requests") as batch:
        batch.drop_column("decision_permission")
