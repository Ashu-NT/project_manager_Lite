# Project Management — Human-Readable Code Columns: Migration Plan

**Date:** 2026-06-01
**Status:** APPROVED (scopes per §2; auto-generate; register prefix = single **REG**; backfill = name token; add Code table columns). **Project — FULLY DONE (A+B+C). Task/Resource/Cost/Register — backend (A+B) DONE + verified.** Remaining: UI (Phase C) for those four — DTO/api threading, presenter `suggest_code`, controller generate slot, dialog `CodeFieldRow`, host wiring, serializer + table "Code" column, update-path code.

**Task/Resource/Cost/Register backend (A+B) — DONE (2026-06-01):**
- ORM code columns + unique indexes: `tasks.task_code` (`ux_tasks_project_code` on project_id+code), `resources.resource_code` (`ux_resources_code` global), `cost_items.cost_code` (`ux_costs_project_code`), `register_entries.entry_code` (`ux_register_entries_project_code`).
- Domain `code` field + `.create(code=...)` on Task/Resource/CostItem/RegisterEntry; mappers both ways.
- Service create auto-generates (`_resolve_*_code`): Task/Cost/Register per-project (`list_by_project`/`list_entries(project_id=)`); Resource global (`list_all`). Manual codes normalized + `assert_code_unique` (`CODE_DUPLICATE`). Prefixes TSK/RES/CST/REG (REG added to `ENTITY_PREFIXES`).
- Migration `m6n7o8p9q0r1_add_pm_entity_codes` (down_revision `l5m6n7o8p9q0`): add 4 nullable columns → scoped name-token backfill → 4 unique indexes; reversible.
- Tests `test_pm_entity_code_generation.py` (6): per-entity autogenerate, per-project scoping (same token, different projects → both 0001), manual duplicate reject. 117 PM tests green across targeted runs.

**Project — COMPLETE (2026-06-01):**
- ORM `projects.project_code` (nullable) + unique `ux_projects_code`; domain `Project.code`; mapper both ways.
- Service `create_project(..., code="")` + `update_project(..., code=None)` → `_resolve_project_code` (normalize manual + `assert_code_unique` with `exclude_id`, or auto-gen `PRJ-<NAME>-NNNN`, global via `project_repo.list_all`). Existing payloads unaffected.
- DTO/API: `ProjectCreateCommand`/`ProjectUpdateCommand`/`ProjectDesktopDto` gained `code`; desktop api threads it; `_serialize_project` emits it.
- UI: presenter `suggest_code` + payload threading; controller `generateEntityCode("project", …)`; `ProjectEditorDialog` `CodeFieldRow` (column-spanning, required, Generate) ↔ `projectCode`; `ProjectsDialogHost` passes `workspaceController`; serializer surfaces `projectCode`; Projects table has a **Code** column.
- Migration `l5m6n7o8p9q0_add_project_code` (down_revision `k4l5m6n7o8p9`): add nullable → backfill name-token → unique; reversible.
- Tests `test_project_code_generation.py` (5); presenter/desktop suites green (49). Runtime-verified dialog Generate → `PRJ-PLAN-0001`.

**Replication recipe (Task/Resource/Cost/Register):** identical vertical. Scopes — Resource global; Task/Cost/Register per-project (service `exists` filtered by `project_id`; per-project unique `(project_id, *_code)`). Register prefix = single `REG`. Each: ORM column+unique, domain field, mapper, service create/update auto-gen+validate, Create/Update command + DTO + desktop api thread, presenter `suggest_code` + payload threading, controller `generateEntityCode` slot, dialog `CodeFieldRow`, host `workspaceController`, serializer + table "Code" column, migration (per-project backfill), tests.
**Context:** PM entities (Project, Task, Resource, Cost, Register/Risk) currently use opaque generated `id`s and have **no** human-readable code column. The shared code-generation system (`CodeGenerator`, `CodeFieldRow`, `generateEntityCode`) is already built and live in Platform/Inventory/Maintenance. This plan adds code columns to PM so the same UX applies — without breaking existing create/update payloads or business logic.
**Builds on:** `DIALOG_DESIGN_SYSTEM_AND_CODE_GENERATION.md`, `PM_DATA_INTEGRITY_*` (alembic head = `k4l5m6n7o8p9`).

---

## 1. Why this is a separate, gated effort

Unlike Platform/Inventory/Maintenance (which already had code columns + `*_CODE_EXISTS` validation), PM has none. Adding them touches **schema + domain + mapper + DTO + commands + services + presenters + controllers + dialogs + tests**. It changes the DB and is irreversible-ish on production data (needs backfill). Hence: explicit approval first, phased rollout, reversible migration, backfill before constraints.

**Guardrails honored:** payload names preserved (code is an *optional, additive* field — empty ⇒ backend auto-generates); business logic unchanged; no page redesign; reuse existing `CodeGenerator`/`CodeFieldRow`/service patterns.

---

## 2. Entities, prefixes, and uniqueness scope (KEY DECISIONS)

| Entity | Table | New column | Prefix | Default segment | **Uniqueness scope** |
|---|---|---|---|---|---|
| Project | `projects` | `project_code` | PRJ | year | **global** (UNIQUE on `project_code`) |
| Task | `tasks` | `task_code` | TSK | project name token | **per project** (UNIQUE on `project_id, task_code`) |
| Resource | `resources` | `resource_code` | RES | resource name token | **global** (resources are a shared pool) |
| Cost | `cost_items` | `cost_code` | CST | year | **per project** (UNIQUE on `project_id, cost_code`) |
| Register entry | `register_entries` | `entry_code` | RSK/ISS/CHG by `entry_type` | year | **per project** (UNIQUE on `project_id, entry_code`) |

Rationale:
- **Project/Resource global** — they are top-level/shared, so codes should be unique across the system (matches how users reference "PRJ-2026-0001").
- **Task/Cost/Register per-project** — they live inside a project; per-project uniqueness keeps codes short and avoids cross-project contention. (Mirrors the data-integrity scoping work.)
- **Register prefix by type** — Register is the unified Risk/Issue/Change workspace; deriving `RSK`/`ISS`/`CHG` from `entry_type` keeps codes meaningful. Alternative: one `REG` prefix. **Decision needed (§9 Q3).**

> ⚠️ **Decisions to confirm before build:** (a) the uniqueness scopes above; (b) register prefix-by-type vs single REG; (c) whether codes are **required** (recommended) or optional going forward.

---

## 3. Migration strategy — detect → add nullable → backfill → constrain

A single Alembic revision (`down_revision = "k4l5m6n7o8p9"`), done in safe order so it never fails on existing data:

1. **Add nullable columns** `project_code`, `task_code`, `resource_code`, `cost_code`, `entry_code` (`String(64)`, nullable).
2. **Backfill** every existing row with a deterministic code (see §4).
3. **Add unique constraints/indexes** per §2 (now safe — all rows populated & unique).
4. (Phase 2 migration, optional) **`ALTER … SET NOT NULL`** once the app always supplies a code.

`downgrade()` drops the constraints then the columns. The migration is reversible.

**Backfill determinism:** order rows by `created_at`/stable id and assign sequential codes per scope. Implemented inside the migration with a small self-contained helper (no app imports) OR by importing `src.core.platform.common.code_generation` (pure module, safe to import in a data migration — preferred for consistency). Codes for existing rows use the **year of `created_at`** segment (e.g. `PRJ-2026-0001`) so they are stable and meaningful.

---

## 4. Backfill detail (per entity)

| Entity | Backfill code | Order/scope |
|---|---|---|
| Project | `PRJ-<created_year>-NNNN` | global sequence by created_at |
| Resource | `RES-<created_year>-NNNN` | global sequence |
| Task | `TSK-<created_year>-NNNN` | sequence **within each project_id** |
| Cost | `CST-<created_year>-NNNN` | within each project_id |
| Register | `<RSK|ISS|CHG>-<created_year>-NNNN` | within each project_id, prefix from entry_type |

Backfill must guarantee uniqueness within the chosen scope (increment sequence on collision). The shared `generate_unique_code(... exists=…)` can drive this with an in-memory "seen" set seeded from already-assigned codes.

---

## 5. Code-touch map (additive only)

Per entity, the same vertical slice already proven in Platform/Inventory/Maintenance:

**Schema/domain**
- `infrastructure/persistence/orm/{project,task,resource,cost_calendar,register}.py` — add the `*_code` column + unique `Index(..., unique=True)` mirroring the migration.
- `domain/**` model — add `code: str` field (default `""`).
- `infrastructure/persistence/mappers/**` — map the column ↔ domain field.

**Application/services**
- Create/Update commands (`*CreateCommand`/`*UpdateCommand`) — add **optional** `code: str = ""` (payload-compatible: existing callers omit it).
- Service create/update — normalize (`normalize_manual_code`) + if empty **auto-generate** via `CodeGenerator` + `assert_code_unique` (scope-aware `exists`) before persisting. Raise `PM_<ENTITY>_CODE_EXISTS` on collision (mirrors `*_CODE_EXISTS` elsewhere).

**UI (controllers/presenters/dialogs)**
- Presenter `suggest_code(payload)` (uniqueness from the relevant list/query, scope-aware).
- Controller `generateEntityCode(entityType, payload)` slot (extend existing PM workspace controllers).
- Dialogs (`ProjectEditorDialog`, `TaskEditorDialog`, `ResourceEditorDialog`, `CostItemEditorDialog`, `RegisterEntryEditorDialog`) — add a `CodeFieldRow` (already reusable) + `<entity>Code` property; dialog hosts pass `workspaceController`.
- Serializers — include the code in the row/state dicts so tables/detail show it.

**Read models / tables**
- Optionally add a "Code" column to the PM DataTables (Projects, Tasks, Resources, Financials, Register) — small serializer + column-def change. Recommended for the enterprise feel; low risk.

---

## 6. Phased rollout

- **Phase A — Schema + backfill (1 migration):** columns + backfill + unique constraints; ORM/domain/mapper. Ship behind tests; verify backfill on a DB copy.
- **Phase B — Service auto-generate + validation:** optional `code` in commands; auto-generate when empty; `assert_code_unique`. Existing payloads keep working (auto-generated).
- **Phase C — UI:** `CodeFieldRow` + generate slots + presenters + dialog hosts; add "Code" table columns.
- **Phase D — (optional) NOT NULL:** once Phase B guarantees a code on every write, a follow-up migration sets the columns `NOT NULL`.

Each phase is independently shippable and reversible. Phases A/B can land without UI (codes auto-generate) — the UI in C just exposes/edits them.

---

## 7. Tests

- Migration/backfill: unit-test the backfill helper (deterministic, unique within scope) on an in-memory dataset.
- Service: create-without-code auto-generates a unique code; create-with-duplicate-code raises `PM_*_CODE_EXISTS`; per-project scoping (same task_code allowed in different projects; blocked within one).
- Presenter `suggest_code`: prefix + token + increment (mirror `test_admin_code_generation.py`).
- Dialog: `CodeFieldRow` Generate populates the code (offscreen runtime test, as done for the other modules).

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Backfill collisions / non-determinism | Scope-aware sequential assignment with `exists` guard; test on a prod DB copy first. |
| Migration fails on dirty/huge data | nullable→backfill→constrain ordering; batched backfill; reversible downgrade. |
| Payload breakage | `code` is optional/additive everywhere; empty ⇒ auto-generate. No existing caller changes. |
| Two write paths create same code concurrently | DB unique constraint is the backstop (raises `*_CODE_EXISTS`), same as other modules. |
| Register prefix ambiguity | Decide RSK/ISS/CHG-by-type vs single REG (§9 Q3) before Phase A. |

---

## 9. Open questions (confirm before Phase A)

1. **Uniqueness scopes** as in §2 — OK? (Project/Resource global; Task/Cost/Register per-project.)
2. **Codes required or optional** going forward? (Recommended: required via Phase D `NOT NULL`; until then auto-generated.)
3. **Register code prefix:** per-type `RSK/ISS/CHG` (meaningful) **or** single `REG`?
4. **Backfill segment:** year (`PRJ-2026-0001`) — OK, or prefer name token (`PRJ-PLANT-0001`) for existing rows?
5. **Add a visible "Code" column** to the PM list tables (Projects/Tasks/Resources/Financials/Register)? (Recommended.)

---

## 10. Effort estimate

~5 ORM + 5 domain + 5 mapper + ~10 command/service files + 5 presenters + 5 controller slots + 5 dialogs + serializers + 1 migration + tests. Mechanical and pattern-identical to the three modules already done — but spread across the full PM stack, so it's the largest single slice. Suggest landing **Phase A+B first** (schema + auto-generate, no UI), verify, then **Phase C** (UI).
