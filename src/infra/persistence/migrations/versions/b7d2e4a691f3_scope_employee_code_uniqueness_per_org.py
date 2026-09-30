"""Employee code uniqueness becomes organization-scoped, not global.

Revision ID: b7d2e4a691f3
Revises: a3f6b1d9c852
Create Date: 2026-09-30 00:00:01.000000

Employee Number is business identity scoped to the organization that
assigned it, not a tenant-wide or database-wide primary key -- the
application layer's own duplicate check was already organization-scoped
(get_by_code_for_organization); the database's inline UNIQUE(employee_code)
table constraint (plus a redundant explicit unique index) was the
mismatched, overly strict layer.

SQLite cannot drop an inline table-level UNIQUE constraint via ALTER TABLE
-- it has no name to target (it is enforced by an internal
sqlite_autoindex_*, not a user index), so batch-mode's usual reflect-and-
diff approach cannot remove it. This migration instead rebuilds the table
explicitly: create the corrected shape, copy every row across unchanged,
drop the old table, rename the new one into place, then recreate every
index (the new composite unique index replaces the old global one).

Reports (and refuses to proceed past) any pre-existing duplicate
(organization_id, employee_code) pair rather than silently resolving it --
none are expected (the app-layer check was already organization-scoped),
but this is verified against the real data before the schema changes,
never assumed.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7d2e4a691f3'
down_revision: str | Sequence[str] | None = 'a3f6b1d9c852'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_TABLE = "employees"
_NEW_TABLE = "_employees_new"

_COLUMNS_DDL = """
    id VARCHAR NOT NULL,
    tenant_id VARCHAR,
    employee_code VARCHAR(64) NOT NULL,
    full_name VARCHAR(256) NOT NULL,
    organization_id VARCHAR NOT NULL,
    department_id VARCHAR NOT NULL,
    department VARCHAR(256),
    site_id VARCHAR,
    site_name VARCHAR(256),
    title VARCHAR(256),
    employment_type VARCHAR(9) DEFAULT 'FULL_TIME' NOT NULL,
    email VARCHAR(256),
    phone VARCHAR(64),
    is_active BOOLEAN DEFAULT '1' NOT NULL,
    user_id VARCHAR,
    version INTEGER DEFAULT '1' NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_employees_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
    CONSTRAINT fk_employees_site_id_sites FOREIGN KEY(site_id) REFERENCES sites (id) ON DELETE SET NULL,
    CONSTRAINT fk_employees_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE SET NULL,
    CONSTRAINT fk_employees_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL,
    CONSTRAINT fk_employees_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
"""
_COPY_COLUMNS = (
    "id, tenant_id, employee_code, full_name, organization_id, department_id, department, "
    "site_id, site_name, title, employment_type, email, phone, is_active, user_id, version"
)


def upgrade() -> None:
    connection = op.get_bind()

    duplicates = connection.execute(
        sa.text(
            """
            SELECT organization_id, employee_code, COUNT(*) AS c
            FROM employees
            GROUP BY organization_id, employee_code
            HAVING c > 1
            """
        )
    ).fetchall()
    if duplicates:
        rows = ", ".join(f"org {row[0]} / code {row[1]} ({row[2]} rows)" for row in duplicates)
        raise RuntimeError(
            "Cannot scope employee_code uniqueness to (organization_id, employee_code): the "
            f"following duplicate pairs already exist -- resolve them manually, then re-run this "
            f"migration: {rows}"
        )

    connection.execute(sa.text(f"CREATE TABLE {_NEW_TABLE} ({_COLUMNS_DDL})"))
    connection.execute(
        sa.text(f"INSERT INTO {_NEW_TABLE} ({_COPY_COLUMNS}) SELECT {_COPY_COLUMNS} FROM {_OLD_TABLE}")
    )
    connection.execute(sa.text(f"DROP TABLE {_OLD_TABLE}"))
    connection.execute(sa.text(f"ALTER TABLE {_NEW_TABLE} RENAME TO {_OLD_TABLE}"))

    op.create_index("idx_employees_tenant", _OLD_TABLE, ["tenant_id"], unique=False)
    op.create_index("idx_employees_organization", _OLD_TABLE, ["organization_id"], unique=False)
    op.create_index("idx_employees_department", _OLD_TABLE, ["department_id"], unique=False)
    op.create_index("idx_employees_site", _OLD_TABLE, ["site_id"], unique=False)
    op.create_index("idx_employees_active", _OLD_TABLE, ["is_active"], unique=False)
    op.create_index("idx_employees_user", _OLD_TABLE, ["user_id"], unique=False)
    op.create_index(
        "idx_employees_org_code", _OLD_TABLE, ["organization_id", "employee_code"], unique=True
    )


def downgrade() -> None:
    connection = op.get_bind()

    duplicates = connection.execute(
        sa.text("SELECT employee_code, COUNT(*) AS c FROM employees GROUP BY employee_code HAVING c > 1")
    ).fetchall()
    if duplicates:
        rows = ", ".join(f"{row[0]} ({row[1]} rows)" for row in duplicates)
        raise RuntimeError(
            "Cannot restore global employee_code uniqueness: the following codes are now "
            f"duplicated across organizations -- resolve them manually, then re-run this "
            f"downgrade: {rows}"
        )

    connection.execute(
        sa.text(f"CREATE TABLE {_NEW_TABLE} ({_COLUMNS_DDL.replace('employee_code VARCHAR(64) NOT NULL,', 'employee_code VARCHAR(64) NOT NULL UNIQUE,')})")
    )
    connection.execute(
        sa.text(f"INSERT INTO {_NEW_TABLE} ({_COPY_COLUMNS}) SELECT {_COPY_COLUMNS} FROM {_OLD_TABLE}")
    )
    connection.execute(sa.text(f"DROP TABLE {_OLD_TABLE}"))
    connection.execute(sa.text(f"ALTER TABLE {_NEW_TABLE} RENAME TO {_OLD_TABLE}"))

    op.create_index("idx_employees_tenant", _OLD_TABLE, ["tenant_id"], unique=False)
    op.create_index("idx_employees_organization", _OLD_TABLE, ["organization_id"], unique=False)
    op.create_index("idx_employees_department", _OLD_TABLE, ["department_id"], unique=False)
    op.create_index("idx_employees_site", _OLD_TABLE, ["site_id"], unique=False)
    op.create_index("idx_employees_active", _OLD_TABLE, ["is_active"], unique=False)
    op.create_index("idx_employees_user", _OLD_TABLE, ["user_id"], unique=False)
    op.create_index("idx_employees_code", _OLD_TABLE, ["employee_code"], unique=True)
