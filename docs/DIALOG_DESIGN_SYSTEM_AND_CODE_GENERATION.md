# Enterprise Dialog Design System & Code Generation

**Date:** 2026-05-31
**Status:** Foundations + **Platform admin (7)** + **Inventory catalog (Category, Item, Storeroom)** + **Maintenance assets (Asset, Component, Location, System)** wired end-to-end. All existing-code modules done. Remaining: PM code columns (separate, explicit decision — schema change).
**Builds on:** `DIALOG_ARCHITECTURE_MIGRATION_PLAN.md`, `INLINE_MESSAGE_STANDARDIZATION_*`

---

## 1. Dialog audit — summary

`find src/ui_qml -name "*Dialog*.qml"` → **69 dialog files**: Project Management 20, Inventory/Procurement 17, Maintenance 16, Platform 12, shared 4.

**Standardization state: already compliant.** A scan for raw controls inside dialog files found:

| Raw control | Dialog files containing it |
|---|---|
| `Text {` | 0 |
| `TextField {` | 0 |
| `ComboBox {` | 0 |
| `Button {` | 0 |
| `Label {` (raw) | 1 (single stray — see §2) |

Every editor dialog already extends `AppWidgets.EntityDialog` (consistent header/subtitle/InlineMessage area/footer with primary-right, cancel-left, destructive styling) and uses `AppControls.Label/TextField/ComboBox/DateField/CheckBox/PrimaryButton/SecondaryButton` + `AppWidgets.InlineMessage` + `Theme.AppTheme` tokens. Submit/validation/error display was standardized in the InlineMessage work (`submitDialog()` + host `_handleResult` → errors shown inside the modal, dialog stays open on failure). So requirements **#1–#10 of "Main requirements" are essentially satisfied** by existing components; this effort does not re-skin dialogs.

## 2. Dialogs with gaps

- **Missing/raw controls:** only 1 stray raw `Label {` flagged by the scan (to confirm + convert to `AppControls.Label`). No raw inputs/buttons anywhere.
- **Required-field indicator:** there was **no consistent required-field marker** across dialogs. The new `CodeFieldRow` introduces a `required` asterisk; the same convention can be extended to other labelled rows if desired (follow-up).
- **Code fields without a generator:** dialogs with code fields offered no "Generate" affordance and relied on free-text entry (see §6).

## 3. Updated / new reusable components

- **NEW `AppWidgets.CodeFieldRow`** (`shared/qml/App/Widgets/CodeFieldRow.qml`, registered in `qmldir`). Labelled code input + optional **Generate** button, built only from `AppControls.Label/TextField/SecondaryButton` + `AppWidgets.InlineMessage` + `Theme.AppTheme`.
  - Props: `label, value, placeholderText, required, helperText, errorText, generateVisible, generateEnabled, busy`.
  - Signals: `valueEdited(string)`, `generateRequested()`.
  - Syncs external value changes (e.g. after Generate) into the field without a two-way binding loop; shows `errorText` via InlineMessage (danger), else `helperText` as a caption.
- `EntityDialog` / `CenteredDialog` / `ConfirmationDialog` are reused unchanged.

## 4. Shared code generator (backend)

**NEW `src/core/platform/common/code_generation.py`** — repository-agnostic, deterministic, meaningful codes (not random):

- `CodeGenerator.generate(entity_type, *, exists, name=None, context=None, year=None, use_year=False, …)` →
  `CLI-ACME-0001`, `PRJ-2026-0001`, `RES-ELEC-0003`, `ITM-PUMP-0007`, `PO-2026-0042`, `TSK-0001`.
- `ENTITY_PREFIXES` map covering PRJ/TSK/RES/CLI/VEN/ITM/PO/WO/AST/DOC/RSK/CST (+ ORG/SITE/DEPT/EMP/PTY/CAT/STR/LOC/CMP/SYS/REQ/RCV).
- Helpers: `sanitize_token` (uppercase, drop unsafe chars, first-word token, max-length), `compose_code`, `generate_unique_code` (lowest free sequence via injected `exists`), `normalize_manual_code`, `is_valid_code`, `assert_code_unique` (raises `CODE_DUPLICATE`).
- **Uniqueness** is enforced via an `exists(code) -> bool` callback the caller wires to the relevant repository, so the backend — never QML — validates uniqueness. Manual codes are normalized + validated the same way.

## 5. Tests

**NEW `src/tests/platform/test_code_generation.py`** — **38 tests, all passing**: token sanitization, code composition/width, unique-sequence increment, exhaustion guard, manual-code normalization + validity, duplicate assertion, and `CodeGenerator` strategies (name token, year, context override, increment-over-existing, plain prefix, custom/derived prefix, blank-entity error).

## 6. Code-field reality per module (drives wiring)

| Module | Entities with a human-readable code column | Notes |
|---|---|---|
| **Platform** | organization, site, department, employee, party, document, document-structure | Codes are **user-entered**, validated by controller; no generator today → best CodeFieldRow candidates. |
| **Inventory** | item, category, storeroom, location + PO/requisition/receipt/transaction/cycle-count **numbers** | Numbers already generated but as **random hex** (`INV-PO-xxxxxxxxxx`), not meaningful sequences. |
| **Maintenance** | asset, component, location, system | `find_*_by_code` lookups exist; codes user-entered. |
| **Project Management** *(requested focus)* | **none** — Project/Task/Resource/Cost/Risk use opaque generated `id`s. Only `skill_code` / `certification_code` exist. | **No `*_code` column to generate into without a schema change.** |

> ⚠️ **Key decision needed:** the requested focus module (PM) has no entity code fields. Wiring `generateProjectCode`/`projectCode` into PM dialogs would require **adding new code columns** (Alembic migration + domain/DTO/payload changes) — which conflicts with "do not break existing payloads / preserve business logic / do not redesign." See §7.

## 7. Platform admin — DONE (all 7 dialogs) + replication recipe for other modules

**Implemented end-to-end for every Platform admin editor dialog** (Organization→ORG, Site→SITE, Department→DEPT, Employee→EMP, Party→PTY, Document→DOC, DocumentStructure→DST):
- Presenter `suggest_code(payload)` → `CodeGenerator` + uniqueness against the entity's `list_*` API (name token from display field; year fallback).
- Child controller `generateCode(payload)` slot (per entity).
- Generic `PlatformAdminWorkspaceController.generateEntityCode(entityType, payload)` dispatch slot — one slot serves all admin dialogs.
- Each dialog uses `AppWidgets.CodeFieldRow` (visible label, `required`, Generate) backed by a `property string <entity>Code`; `AdminDialogHost` passes `workspaceController` to each.
- Backend uniqueness on save **already enforced** by the org services (`*_CODE_EXISTS` via `get_by_code`) — generated and manual codes both validated.
- Runtime-verified (Organization): clicking Generate populates `ORG-ACME-0001`. Presenter tests cover Site/Party/Document/Structure too.

**Replication recipe for Inventory / Maintenance (where code fields already exist):**
1. Presenter/service: add a `suggest_code`/`generate_code` using `CodeGenerator.generate(<entity>, exists=<repo/list>, name=<display field>)`.
2. Controller: add a `generateCode`/`generateEntityCode` slot.
3. Dialog: swap the code `TextField` for `CodeFieldRow` (track value in `property string <entity>Code`; update formData/_loadDraft/submitDialog), add `workspaceController` + `onGenerateRequested`; the dialog host passes the controller.
4. Ensure the service validates code uniqueness on save (`normalize_manual_code` + `assert_code_unique` available for any that don't yet — Inventory/Maintenance have `find_*_by_code`/`normalize_*_code`).
5. Add a presenter/service test (mirror `test_admin_code_generation.py`).

**Inventory catalog — DONE:** Category (CAT), Item (ITM), Storeroom (STR). `suggest_*_code` added to `catalog_workspace_presenter` (category/item via `list_categories`/`list_items`) and `inventory_workspace_presenter` (storeroom via `list_storerooms`); `generateEntityCode(entityType, payload)` slot on `catalog_workspace_controller` + `inventory_workspace_controller`; `CodeFieldRow` (column-spanning) in CategoryEditorDialog/ItemEditorDialog/StoreroomEditorDialog; `CatalogDialogHost`/`InventoryDialogHost` pass `workspaceController`. Backend already rejects dup codes (`INVENTORY_*_CODE_EXISTS`). Runtime-verified (Category → `CAT-SPAR-0001`); tests in `test_inventory_code_generation.py`.

**Maintenance assets — DONE:** Asset (AST), Component (CMP), Location (LOC), System (SYS). `suggest_*_code` (shared `_suggest_code` helper) in `assets_workspace_presenter` (via `list_assets/components/locations/systems`); `generateEntityCode(entityType, payload)` dispatch slot on `assets_workspace_controller`; `CodeFieldRow` (column-spanning) in Asset/Component/Location/SystemEditorDialog; `AssetsDialogHost` passes `workspaceController`. Backend already rejects dup codes (`MAINTENANCE_*_CODE_EXISTS`). Runtime-verified (Asset → `AST-CONV-0001`); tests in `test_maintenance_code_generation.py`.

**Rollout order:** Platform admin (done) → Inventory catalog (done) → Maintenance assets (done). PM only if code columns are introduced (separate, explicit decision).

## 8. Files changed

Foundations:
- NEW `src/core/platform/common/code_generation.py`
- NEW `src/tests/platform/test_code_generation.py`
- NEW `src/ui_qml/shared/qml/App/Widgets/CodeFieldRow.qml` + EDIT `.../App/Widgets/qmldir`
- NEW `docs/DIALOG_DESIGN_SYSTEM_AND_CODE_GENERATION.md`

Platform admin wiring:
- EDIT presenters: `organization_catalog_presenter.py`, `site_catalog_presenter.py`, `department_catalog_presenter.py`, `employee_catalog_presenter.py`, `party_catalog_presenter.py`, `document_catalog_presenter.py`, `document_management_presenter.py` (add `suggest_code`)
- EDIT controllers: `admin_console_controller.py` (generic `generateEntityCode`), `organization_controller.py`, `site_controller.py`, `department_controller.py`, `employee_controller.py`, `party_controller.py`, `document_controller.py`, `document_structure_controller.py` (add `generateCode`)
- EDIT dialogs: `OrganizationEditorDialog`, `SiteEditorDialog`, `DepartmentEditorDialog`, `EmployeeEditorDialog`, `PartyEditorDialog`, `DocumentEditorDialog`, `DocumentStructureEditorDialog` (CodeFieldRow)
- EDIT `workspaces/admin/AdminDialogHost.qml` (pass `workspaceController` to the 7 editor dialogs)
- NEW `src/tests/platform/test_admin_code_generation.py`

## 9. Validation

- `python -m pytest src/tests/platform/test_code_generation.py` → **38 passed**.
- `CodeFieldRow.qml` compiles + instantiates via `App.Widgets` (offscreen QQmlComponent); external value sync verified.

## 10. Remaining (next phases)

- Resolve the PM code-column decision (§6/§7).
- Wire `CodeFieldRow` + generator slots + save-time validation into the modules that have code fields, with tests.
- Optionally migrate Inventory's random `INV-PO-xxxx` numbers to the meaningful `PO-2026-NNNN` format (separate, since it changes generated values).
- Optionally extend the `required` asterisk convention to non-code labelled rows for a fully consistent required indicator.
