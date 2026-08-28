# R5H.1 PostgreSQL Integration Evidence

## Status

R5H.1 is complete. Evidence was produced on 2026-08-26 against the dedicated
Dockerized PostgreSQL 16 database `project_manager_r5h`. The suite is opt-in
and does not replace SQLite unit/domain tests.

## Reproducible Environment

The stack in `src/tests/integration/postgresql/compose.yml` separates roles:

| Role | Purpose | Security properties |
|---|---|---|
| `r5h_admin` | Container bootstrap and controlled fixture loading | Superuser; never used for RLS assertions |
| `r5h_migrator` | Alembic and schema ownership | NOSUPERUSER, NOBYPASSRLS, NOINHERIT |
| `app_runtime` | Application reads, attacks, concurrency, and plans | NOSUPERUSER, NOBYPASSRLS, NOINHERIT; owns zero application tables |

Every test session verifies the dedicated database name, recreates its public
schema, runs Alembic to `head` as `r5h_migrator`, and grants runtime DML and
sequence access to `app_runtime`. Application sessions use the real
`UserSessionContext` and `configure_session_rls_context()` transaction hook.

```powershell
./tools/run_r5h1_postgresql.ps1
```

Use `-KeepContainer` for inspection or `-Action down` to remove the stack.

## Fresh-Schema Findings

The first live Alembic run found two PostgreSQL defects hidden by SQLite:

1. Five Boolean columns emitted integer SQL defaults. The fresh baseline now
   uses dialect-safe `sa.true()` and `sa.false()` defaults.
2. `resources.site_id` referenced `sites` before that table existed. Its
   constraint now uses the baseline's delayed-FK mechanism and remains enforced
   on PostgreSQL and SQLite.

No production architecture was changed to support the container.

## Security Evidence

The live suite proves:

- `app_runtime` is neither superuser nor BYPASSRLS and owns no protected table;
- all classified direct and R5 parent-scoped tables have ENABLE and FORCE RLS;
- SELECT, INSERT, UPDATE, and DELETE policies exist for every protected table;
- same-tenant cross-organization and cross-tenant rows are invisible;
- cross-scope UPDATE and DELETE affect zero rows and INSERT violates WITH CHECK;
- absent runtime scope is deny-safe;
- direct bypass attempts fail for `resource_skills`,
  `resource_certifications`, `project_resources`, `tasks`, `task_assignments`,
  and `task_skill_requirements`;
- the existing optimistic-concurrency helper rejects a stale TimeEntry update
  through `app_runtime`.

## Scale Results

The same instance loads separate 10,000 and 50,000 Resource scopes, with one
TaskAssignment, TimeEntry, and submitted TimesheetPeriod per Resource. Seven
warm measurements are recorded after one warm-up call.

| Authoritative reader | 10k p50 / p95 | 50k p50 / p95 | Statements | Gate |
|---|---:|---:|---:|---:|
| Resource Catalog | 38.98 / 43.27 ms | 121.78 / 132.38 ms | 3 | p95 <= 200 ms |
| Timesheets Resource selector | 21.05 / 24.21 ms | 58.35 / 63.06 ms | 2 | bounded |
| Review Queue | 45.50 / 49.53 ms | 142.30 / 179.03 ms | 2 | p95 <= 200 ms |
| Resource Inspector | 10.59 / 12.26 ms | 7.00 / 9.22 ms | bounded | p95 <= 100 ms |
| Availability assignment demand | 4.48 / 5.52 ms | 4.05 / 5.63 ms | bounded | p95 <= 200 ms |
| Timesheet entries | 15.81 / 17.05 ms | 38.23 / 40.92 ms | bounded | p95 <= 200 ms |
| Timesheet history | 30.92 / 37.86 ms | 39.87 / 42.07 ms | bounded | p95 <= 200 ms |
| Review Queue Inspector | 30.87 / 40.52 ms | 39.09 / 48.48 ms | bounded | p95 <= 200 ms |

The initial Review Queue plan took about 17 seconds because ownership used a
correlated assignment lookup and all scoped periods were aggregated before
pagination. The final reader resolves ownership once, pages authoritative
periods before aggregation for compatible sorts, bounds ownership to selected
Resources, and returns distinct project IDs in the same aggregate. Restricted,
project-search, and aggregate-sort paths retain their authorization-aware shape.

## Query Plans

`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` ran through `app_runtime` with real
tenant/organization session settings. Representative 50k execution times:

| Query | Execution time |
|---|---:|
| Resource Catalog page | 42.033 ms |
| Review Queue page shape | 84.762 ms |
| Timesheets Resource selector | 28.623 ms |
| Resource Inspector | 0.274 ms |
| Availability assignment demand | 0.235 ms |
| Timesheet entries | 17.513 ms |
| Timesheet history | 0.308 ms |

The gates are green without a speculative index. Full machine-readable plans
and samples are written to ignored local artifact
`.security-evidence/r5h1_postgresql.json`.

## Verification

```text
PostgreSQL security/concurrency: 14 passed
Complete PostgreSQL R5H.1 suite: 18 passed in 32.51s
Focused Review Queue/Timesheets compatibility: 13 passed
```

R5H.1 closes the PostgreSQL runtime-role, RLS-negative, child-bypass,
fresh-Alembic, optimistic-concurrency, and named 10k/50k query-evidence gate.
It does not manufacture manual QML interaction evidence or certify unrelated
R5/R6 surfaces.
