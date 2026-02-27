# Migration Module

This module documents schema evolution and startup migration behavior.

## Source Folder

- `migration/`

## Components

- `alembic.ini`
- `env.py`
- `script.py.mako`
- `versions/*.py` migration revisions
- `README` (Alembic default placeholder)

## Runtime Integration

Migrations are executed automatically during app startup through:

- `infra.migrate.run_migrations(db_url)`

Path discovery supports:

- development layout
- PyInstaller onefile extraction directory
- PyInstaller onedir and nested layout fallbacks

This ensures packaged releases still migrate DB schema without manual steps.

## Current Revision Themes

Existing migration set includes:

- baseline tables and fields
- auth/role/permission tables
- optimistic-locking version columns
- audit and approval tables
- baseline task snapshot enhancements

## Operational Notes

- migration execution target is always `head`
- failure to locate migration assets is treated as startup error
- schema is intended to be forward-evolved via Alembic revisions, not ad hoc DDL
