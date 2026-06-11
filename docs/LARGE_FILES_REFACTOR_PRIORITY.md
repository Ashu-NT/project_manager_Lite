# Large Files — Refactor Priority List

**Generated:** 2026-06-11 (updated 2026-06-11)  
**Threshold:** > 350 effective LOC  
**Effective LOC definition:** total lines minus blank lines, comment lines, import statements, `__all__` declarations, and docstrings  
**Total files:** 106  
**Excluded:** `resources/resources_rc.py` (321 530 LOC — generated Qt resource file, do not refactor)

Priority is ordered by **production impact first** (services → APIs → controllers/presenters → infrastructure → QML → tests → migrations).  
Within each tier, files are ordered by LOC descending.

---

## Priority Tier 1 — Application Services & Domain Models (Business Logic)

These own business rules and are hardest to test, reason about, and extend at scale.  
Target: split by command/query, by aggregate, or extract mixins into purpose-named units.

| LOC | File |
|----:|------|
|  915 | `src/core/platform/auth/application/auth_service.py` |
|  809 | `src/core/modules/maintenance/application/work_orders/work_order_service.py` |
|  740 | `src/core/modules/inventory_procurement/application/inventory/foundation_service.py` |
|  637 | `src/core/modules/maintenance/application/reliability/reliability_service.py` |
|  551 | `src/core/modules/maintenance/application/assets/asset_service.py` |
|  548 | `src/core/modules/maintenance/application/preventive/services/plan_service.py` |
|  548 | `src/core/modules/inventory_procurement/application/catalog/service.py` |
|  540 | `src/core/modules/maintenance/application/work_orders/work_order_material_requirement_service.py` |
|  531 | `src/core/platform/documents/application/document_service.py` |
|  527 | `src/core/modules/maintenance/application/preventive/services/plan_task_service.py` |
|  510 | `src/core/modules/maintenance/application/documents/document_service.py` |
|  491 | `src/core/modules/project_management/application/tasks/queries/dependency_diagnostics.py` |
|  472 | `src/core/modules/maintenance/application/preventive/services/generation_service.py` |
|  461 | `src/core/modules/maintenance/application/work_requests/work_request_service.py` |
|  460 | `src/core/modules/maintenance/application/assets/component_service.py` |
|  448 | `src/core/platform/calendar/application/enterprise_calendar_resolver.py` |
|  448 | `src/core/platform/calendar/domain/enterprise_calendar.py` |
|  426 | `src/core/modules/project_management/application/scheduling/baselines/baseline_service.py` |
|  423 | `src/core/modules/maintenance/application/reliability/sensor_service.py` |
|  420 | `src/core/modules/maintenance/application/reliability/downtime_event_service.py` |
|  417 | `src/core/modules/inventory_procurement/application/inventory/reservation_service.py` |
|  417 | `src/core/modules/inventory_procurement/application/procurement/purchasing_lifecycle.py` |
|  415 | `src/core/platform/data_exchange/service.py` |
|  390 | `src/core/platform/time/application/timesheet_support.py` |
|  389 | `src/core/modules/maintenance/domain/preventive/schedule.py` |
|  381 | `src/core/modules/inventory_procurement/domain/procurement/purchasing.py` |
|  379 | `src/core/modules/maintenance/application/common/support.py` |
|  374 | `src/core/modules/inventory_procurement/application/inventory/stock_control_adjustments.py` |
|  365 | `src/core/platform/department/application/department_service.py` |
|  365 | `src/core/modules/project_management/application/financials/costs/cost_policy_engine.py` |
|  355 | `src/core/modules/maintenance/application/work_orders/work_order_task_step_service.py` |
|  352 | `src/core/modules/maintenance/domain/reliability/monitoring.py` |

---

## Priority Tier 2 — API / Desktop Layer

Orchestration code between services and the UI. Complex dispatch, serialization, and business rules mixed together. Target: split by workspace section or extract serializers.

| LOC | File |
|----:|------|
|  715 | `src/core/modules/maintenance/api/desktop/preventive/api.py` |
|  679 | `src/core/modules/maintenance/api/desktop/assets/api.py` |
|  638 | `src/api/desktop/platform/enterprise_calendar.py` |
|  635 | `src/api/desktop/runtime.py` |
|  610 | `src/core/modules/inventory_procurement/api/desktop/inventory/foundation.py` |
|  532 | `src/core/modules/inventory_procurement/api/desktop/procurement/api.py` |
|  531 | `src/core/modules/inventory_procurement/api/desktop/pricing/api.py` |
|  508 | `src/api/desktop/platform/support.py` |
|  494 | `src/core/modules/project_management/api/desktop/tasks/api.py` |
|  455 | `src/core/modules/maintenance/api/desktop/work_orders/api.py` |
|  451 | `src/core/modules/maintenance/api/desktop/planner/api.py` |

---

## Priority Tier 3 — Controllers & Presenters (UI Logic)

QML controller/presenter files are the glue between services and the view layer. Very long files here make UI bugs hard to trace. Target: split by section or extract sub-controllers.

| LOC | File |
|----:|------|
|  514 | `src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py` |
|  467 | `src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py` |
|  466 | `src/ui_qml/modules/project_management/controllers/tasks/pm_task_list_controller.py` |
|  454 | `src/ui_qml/platform/presenters/document_management_presenter.py` |
|  436 | `src/ui_qml/modules/project_management/controllers/portfolio/portfolio_workspace_controller.py` |
|  420 | `src/ui_qml/modules/inventory_procurement/controllers/inventory/inventory_workspace_controller.py` |
|  395 | `src/ui_qml/modules/inventory_procurement/controllers/procurement/procurement_workspace_controller.py` |

---

## Priority Tier 4 — Infrastructure (ORM, Repositories, Mappers, Reporting)

Infrastructure files are stable but large ones indicate aggregated responsibility. Target: split by aggregate root or module boundary.

| LOC | File |
|----:|------|
| 1250 | `src/core/modules/maintenance/infrastructure/persistence/repositories/repository.py` |
| 1155 | `src/core/modules/maintenance/infrastructure/persistence/orm/models.py` |
| 1022 | `src/core/modules/maintenance/infrastructure/persistence/mappers/mapper.py` |
|  504 | `src/core/modules/maintenance/infrastructure/reporting/service.py` |
|  491 | `src/core/modules/maintenance/infrastructure/reporting/documents.py` |
|  445 | `src/core/modules/inventory_procurement/infrastructure/reporting/service.py` |
|  439 | `src/core/platform/infrastructure/persistence/repositories/enterprise_calendar.py` |
|  425 | `src/core/modules/inventory_procurement/infrastructure/persistence/repositories/inventory.py` |
|  397 | `src/core/modules/inventory_procurement/infrastructure/importers/service.py` |
|  387 | `src/core/modules/inventory_procurement/infrastructure/importers/parsing.py` |
|  370 | `src/core/modules/inventory_procurement/infrastructure/integrations/maintenance_materials.py` |

---

## Priority Tier 5 — QML Workspace Files

Large QML orchestrators make it hard to trace UI state bugs. Target: extract panels, sections, and list pages into sub-files (the established workspace pattern).

| LOC | File |
|----:|------|
|  841 | `src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml` |
|  688 | `src/ui_qml/shared/qml/App/Widgets/DataTable.qml` |
|  607 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminCalendarDetailPage.qml` |
|  523 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioDetailPanel.qml` |
|  512 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminSiteDetailPage.qml` |
|  490 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminPartyDetailPage.qml` |
|  482 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDocumentsDetailPage.qml` |
|  479 | `src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingDetailPanel.qml` |
|  473 | `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml` |
|  466 | `src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets/DashboardChartCard.qml` |
|  462 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDepartmentDetailPage.qml` |
|  438 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEmployeeDetailPage.qml` |
|  413 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksWorkspacePage.qml` |
|  406 | `src/ui_qml/platform/qml/workspaces/admin/sections/AdminAuditSection.qml` |
|  384 | `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml` |
|  377 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioBottomPanel.qml` |
|  376 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminUserDetailPage.qml` |
|  374 | `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspaceState.qml` |
|  372 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEntityDetailPage.qml` |
|  366 | `src/ui_qml/shell/qml/LoginWindow.qml` |
|  366 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminOrganizationDetailPage.qml` |
|  364 | `src/ui_qml/modules/project_management/qml/workspaces/register/panels/RegisterDetailPanel.qml` |
|  363 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksTimeEntriesSection.qml` |

---

## Priority Tier 6 — Composition & Config

Wiring files. These grow naturally but signal architecture smell when very large.

| LOC | File |
|----:|------|
|  437 | `src/infra/composition/maintenance_registry.py` |
|  398 | `src/infra/composition/project_registry.py` |

---

## Priority Tier 7 — Tests

Large test files reduce test isolation and increase CI time. Target: split by scenario group.

| LOC | File |
|----:|------|
| 3008 | `src/tests/project_management/test_project_management_desktop_api.py` |
| 2253 | `src/tests/platform/test_qml_platform_presenters.py` |
| 2065 | `src/tests/project_management/test_qml_project_management_presenters.py` |
|  919 | `src/tests/maintenance/test_maintenance_foundation.py` |
|  901 | `src/tests/maintenance/test_maintenance_desktop_api.py` |
|  852 | `src/tests/maintenance/test_maintenance_persistence.py` |
|  676 | `src/tests/inventory_procurement/test_inventory_procurement_desktop_api.py` |
|  669 | `src/tests/inventory_procurement/test_qml_inventory_procurement_presenters.py` |
|  614 | `src/tests/architecture/test_qml_architecture_guardrails.py` |
|  555 | `src/tests/architecture/test_architecture_guardrails.py` |
|  550 | `src/tests/platform/test_enterprise_calendar_foundation.py` |
|  467 | `src/tests/inventory_procurement/test_inventory_procurement_purchasing.py` |
|  433 | `src/tests/project_management/test_enterprise_calendar_pm_integration.py` |
|  404 | `src/tests/maintenance/test_qml_maintenance_presenters.py` |
|  378 | `src/tests/test_qml_shared_primitives.py` |
|  365 | `src/tests/path_rewrites.py` |
|  362 | `src/tests/test_exporters_configuration.py` |
|  355 | `src/tests/inventory_procurement/test_qml_inventory_procurement_dialog_hosts.py` |

---

## Priority Tier 8 — Migration Files

Schema files. Rarely changed. Document them but do not refactor.

No migration files currently exceed 350 effective LOC.

---

## Quick Stats by Tier

| Tier | Files | Refactor approach |
|---|---|---|
| 1 — Application Services & Domain | 32 | Split by command/query, aggregate, or mixin |
| 2 — API / Desktop Layer | 11 | Split by workspace section, extract serializers |
| 3 — Controllers / Presenters | 9 | Extract sub-controllers, section presenters |
| 4 — Infrastructure | 11 | Split by aggregate root or bounded context |
| 5 — QML Workspace Files | 23 | Extract panels, sections, list pages |
| 6 — Composition / Config | 2 | Extract sub-registries per module |
| 7 — Tests | 18 | Split by scenario group |
| 8 — Migration Files | 0 | Document only — do not refactor |
| **Total** | **106** | |

---

## Top 10 Highest-Impact Splits

These 10 files alone account for the most technical debt by volume and domain impact:

1. `test_project_management_desktop_api.py` (3008) — split by workspace domain
2. `test_qml_platform_presenters.py` (2253) — split by admin section
3. `test_qml_project_management_presenters.py` (2065) — split by workspace domain
4. `maintenance/repositories/repository.py` (1250) — split by asset, WO, preventive, reliability
5. `maintenance/orm/models.py` (1155) — split by aggregate (asset, WO, preventive, reliability)
6. `maintenance/mappers/mapper.py` (1022) — split by aggregate root
7. `test_maintenance_foundation.py` (919) — split by service group
8. `auth_service.py` (915) — split by auth domain (sessions, tokens, permissions)
9. `test_maintenance_desktop_api.py` (901) — split by service group
10. `test_maintenance_persistence.py` (852) — split by aggregate root

---

## Notable Drops Since Last Audit

Files from the prior list that fell below 350 effective LOC after recent refactors:

| File | Previous raw LOC | Current effective LOC | Status |
|---|---|---|---|
| `timesheets_workspace_controller.py` | 504 | 259 | Refactored — state_setters.py + refresh_service.py extracted, removed from list |
| `tasks_workspace_controller.py` | 670 | 467 | Partially refactored — 8 modules extracted, still in list |
| `collaboration_workspace_controller.py` | 590 | 222 | Refactored — 6 modules extracted, removed from list |
| `admin_console_controller.py` | 1047 | 287 | Refactored — removed from list |
| `scheduling_workspace_controller.py` | 1195 | 514 | Refactored — still in list |
| `projects_workspace_controller.py` | 491 | ~310 | Refactored — removed from list |
| `resources_workspace_controller.py` | 389 | 258 | Refactored — removed from list |
| `access_workspace_controller.py` | 375 | 304 | Refactored — removed from list |
| `data_table_model.py` | 373 | 294 | Refactored — removed from list |
| `catalog_workspace_controller.py` | 525 | 339 | Refactored — removed from list |
| `pricing_workspace_controller.py` | 355 | 228 | Refactored — removed from list |
