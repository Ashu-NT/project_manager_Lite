"""Protect document links through their document and PM comment parents."""

from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_parent_scoped_rls,
    enable_parent_scoped_rls,
)
from src.infra.persistence.migrations.helpers.rls_classification import (
    PARENT_SCOPED_RLS_PREDICATES,
)

revision = "e8b42c1d90af"
down_revision = "d3e7a91c4b52"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    disable_parent_scoped_rls(op, bind, "document_links")
    enable_parent_scoped_rls(
        op, bind, "document_links",
        predicate=PARENT_SCOPED_RLS_PREDICATES["document_links"],
    )


def downgrade():
    disable_parent_scoped_rls(op, op.get_bind(), "document_links")
