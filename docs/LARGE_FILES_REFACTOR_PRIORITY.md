# Large Files — Refactor Priority List

**Generated:** 2026-06-11  
**Threshold:** > 350 LOC  
**Total files:** 171  

Priority is ordered by **production impact first** (services → APIs → controllers/presenters → infrastructure → QML → tests → migrations).  
Within each tier, files are ordered by LOC descending.

---

## Priority Tier 1 — Application Services (Business Logic)

These own business rules and are hardest to test, reason about, and extend at scale.  
Target: split by command/query, by aggregate, or extract mixins into purpose-named units.

| LOC | File |
|----:|------|
| 1025 | `src/core/platform/auth/application/auth_service.py` |
|  921 | `src/core/modules/maintenance/application/work_orders/work_order_service.py` |
|  809 | `src/core/modules/inventory_procurement/application/inventory/foundation_service.py` |
|  713 | `src/core/modules/maintenance/application/reliability/reliability_service.py` |
|  635 | `src/core/modules/maintenance/application/preventive/services/plan_service.py` |
|  613 | `src/core/modules/maintenance/application/work_orders/work_order_material_requirement_service.py` |
|  611 | `src/core/modules/inventory_procurement/application/catalog/service.py` |
|  611 | `src/core/modules/maintenance/application/assets/asset_service.py` |
|  605 | `src/core/modules/maintenance/application/preventive/services/generation_service.py` |
|  595 | `src/core/platform/documents/application/document_service.py` |
|  591 | `src/core/modules/maintenance/application/preventive/services/plan_task_service.py` |
|  568 | `src/core/modules/maintenance/application/documents/document_service.py` |
|  561 | `src/core/modules/project_management/application/tasks/queries/dependency_diagnostics.py` |
|  557 | `src/core/platform/calendar/application/enterprise_calendar_resolver.py` |
|  555 | `src/core/modules/project_management/application/scheduling/baselines/baseline_service.py` |
|  540 | `src/core/modules/maintenance/application/work_requests/work_request_service.py` |
|  522 | `src/core/modules/maintenance/application/common/support.py` |
|  511 | `src/core/modules/maintenance/application/assets/component_service.py` |
|  480 | `src/core/modules/maintenance/application/reliability/sensor_service.py` |
|  476 | `src/core/platform/data_exchange/service.py` |
|  476 | `src/core/modules/inventory_procurement/application/inventory/reservation_service.py` |
|  475 | `src/core/modules/maintenance/application/reliability/downtime_event_service.py` |
|  458 | `src/core/modules/inventory_procurement/application/procurement/purchasing_lifecycle.py` |
|  454 | `src/core/modules/project_management/application/financials/costs/cost_policy_engine.py` |
|  447 | `src/core/platform/time/application/timesheet_support.py` |
|  440 | `src/core/modules/maintenance/domain/preventive/schedule.py` |
|  431 | `src/core/modules/inventory_procurement/domain/procurement/purchasing.py` |
|  422 | `src/core/modules/maintenance/application/work_orders/work_order_task_step_service.py` |
|  412 | `src/core/modules/inventory_procurement/application/inventory/stock_control_adjustments.py` |
|  408 | `src/core/platform/department/application/department_service.py` |
|  402 | `src/core/modules/maintenance/application/reliability/sensor_exception_service.py` |
|  400 | `src/core/modules/project_management/application/scheduling/services/scheduling_engine.py` |
|  397 | `src/core/modules/maintenance/domain/reliability/monitoring.py` |
|  392 | `src/core/modules/inventory_procurement/application/inventory/service.py` |
|  383 | `src/core/modules/inventory_procurement/application/procurement/procurement_lifecycle.py` |
|  383 | `src/core/modules/maintenance/application/work_orders/work_order_task_service.py` |
|  374 | `src/core/platform/calendar/application/enterprise_calendar_service.py` |
|  373 | `src/core/modules/project_management/application/projects/commands/lifecycle.py` |
|  360 | `src/core/modules/maintenance/application/assets/system_service.py` |
|  359 | `src/core/platform/documents/application/document_integration_service.py` |
|  357 | `src/core/modules/inventory_procurement/application/procurement/purchasing_receiving.py` |
|  357 | `src/core/modules/inventory_procurement/application/common/support.py` |
|  354 | `src/core/modules/project_management/application/tasks/commands/lifecycle.py` |

---

## Priority Tier 2 — API / Desktop Layer

Orchestration code between services and the UI. Complex dispatch, serialization, and business rules mixed together. Target: split by workspace section or extract serializers.

| LOC | File |
|----:|------|
|  854 | `src/core/modules/maintenance/api/desktop/preventive/api.py` |
|  820 | `src/api/desktop/runtime.py` |
|  787 | `src/api/desktop/platform/enterprise_calendar.py` |
|  786 | `src/core/modules/maintenance/api/desktop/assets/api.py` |
|  675 | `src/core/modules/inventory_procurement/api/desktop/inventory/foundation.py` |
|  654 | `src/core/modules/project_management/api/desktop/tasks/api.py` |
|  631 | `src/core/modules/inventory_procurement/api/desktop/procurement/api.py` |
|  597 | `src/core/modules/inventory_procurement/api/desktop/pricing/api.py` |
|  591 | `src/api/desktop/platform/support.py` |
|  557 | `src/core/modules/maintenance/api/desktop/work_orders/api.py` |
|  521 | `src/core/modules/maintenance/api/desktop/planner/api.py` |
|  404 | `src/core/modules/maintenance/api/desktop/preventive/serializers.py` |
|  402 | `src/core/modules/inventory_procurement/api/desktop/dashboard.py` |
|  386 | `src/core/modules/maintenance/api/desktop/work_requests/api.py` |
|  382 | `src/core/modules/maintenance/api/desktop/preventive/models.py` |
|  380 | `src/core/modules/project_management/api/desktop/scheduling/api.py` |
|  356 | `src/core/modules/maintenance/api/desktop/reliability/api.py` |

---

## Priority Tier 3 — Controllers & Presenters (UI Logic)

QML controller/presenter files are the glue between services and the view layer. Very long files here make UI bugs hard to trace. Target: split by section or extract sub-controllers.

| LOC | File |
|----:|------|
| 1195 | `src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py` |
| 1046 | `src/ui_qml/platform/controllers/admin/admin_console_controller.py` |
|  881 | `src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py` |
|  650 | `src/ui_qml/modules/inventory_procurement/controllers/inventory/inventory_workspace_controller.py` |
|  609 | `src/ui_qml/modules/inventory_procurement/controllers/procurement/procurement_workspace_controller.py` |
|  590 | `src/ui_qml/modules/project_management/controllers/collaboration/collaboration_workspace_controller.py` |
|  556 | `src/ui_qml/modules/project_management/controllers/tasks/pm_task_list_controller.py` |
|  554 | `src/ui_qml/modules/project_management/controllers/portfolio/portfolio_workspace_controller.py` |
|  525 | `src/ui_qml/modules/inventory_procurement/controllers/catalog/catalog_workspace_controller.py` |
|  520 | `src/ui_qml/platform/presenters/document_management_presenter.py` |
|  504 | `src/ui_qml/modules/project_management/controllers/timesheets/timesheets_workspace_controller.py` |
|  491 | `src/ui_qml/modules/project_management/controllers/projects/projects_workspace_controller.py` |
|  403 | `src/ui_qml/modules/maintenance/controllers/assets/assets_workspace_controller.py` |
|  397 | `src/ui_qml/modules/project_management/presenters/scheduling/workspace_builder.py` |
|  389 | `src/ui_qml/modules/project_management/controllers/resources/resources_workspace_controller.py` |
|  380 | `src/ui_qml/modules/maintenance/presenters/assets/workspace_builder.py` |
|  375 | `src/ui_qml/platform/controllers/admin/access_workspace_controller.py` |
|  373 | `src/ui_qml/shared/models/data_table_model.py` |
|  355 | `src/ui_qml/modules/inventory_procurement/controllers/pricing/pricing_workspace_controller.py` |

---

## Priority Tier 4 — Infrastructure (ORM, Repositories, Mappers)

Infrastructure files are stable but large ones indicate aggregated responsibility. Target: split by aggregate root or module boundary.

| LOC | File |
|----:|------|
| 1489 | `src/core/modules/maintenance/infrastructure/persistence/repositories/repository.py` |
| 1282 | `src/core/modules/maintenance/infrastructure/persistence/orm/models.py` |
| 1203 | `src/core/modules/maintenance/infrastructure/persistence/mappers/mapper.py` |
|  596 | `src/core/modules/maintenance/infrastructure/reporting/service.py` |
|  580 | `src/core/platform/infrastructure/persistence/repositories/enterprise_calendar.py` |
|  549 | `src/core/modules/maintenance/infrastructure/reporting/documents.py` |
|  535 | `src/core/modules/inventory_procurement/infrastructure/persistence/repositories/inventory.py` |
|  519 | `src/core/platform/calendar/domain/enterprise_calendar.py` |
|  508 | `src/core/modules/inventory_procurement/infrastructure/reporting/service.py` |
|  480 | `src/core/modules/inventory_procurement/infrastructure/importers/service.py` |
|  422 | `src/core/modules/inventory_procurement/infrastructure/importers/parsing.py` |
|  422 | `src/core/modules/inventory_procurement/api/desktop/inventory/models.py` |
|  419 | `src/core/modules/inventory_procurement/infrastructure/integrations/maintenance_materials.py` |
|  409 | `src/core/modules/project_management/infrastructure/reporting/exporters/renderers/excel.py` |
|  397 | `src/core/modules/inventory_procurement/infrastructure/persistence/orm/inventory.py` |
|  392 | `src/core/platform/infrastructure/persistence/mappers/enterprise_calendar.py` |
|  377 | `src/core/modules/project_management/infrastructure/reporting/api.py` |
|  376 | `src/core/modules/inventory_procurement/infrastructure/persistence/mappers/inventory.py` |
|  365 | `src/core/modules/maintenance/infrastructure/importers/contracts.py` |
|  363 | `src/core/platform/infrastructure/persistence/orm/enterprise_calendar.py` |

---

## Priority Tier 5 — QML Workspace Files

Large QML orchestrators make it hard to trace UI state bugs. Target: extract panels, sections, and list pages into sub-files (the established workspace pattern).

| LOC | File |
|----:|------|
|  959 | `src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml` |
|  853 | `src/ui_qml/shared/qml/App/Widgets/DataTable.qml` |
|  663 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminCalendarDetailPage.qml` |
|  594 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioDetailPanel.qml` |
|  563 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminSiteDetailPage.qml` |
|  557 | `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml` |
|  542 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminPartyDetailPage.qml` |
|  542 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDocumentsDetailPage.qml` |
|  535 | `src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets/DashboardChartCard.qml` |
|  529 | `src/ui_qml/modules/project_management/qml/workspaces/scheduling/panels/SchedulingDetailPanel.qml` |
|  508 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminDepartmentDetailPage.qml` |
|  495 | `src/ui_qml/platform/qml/workspaces/admin/sections/AdminAuditSection.qml` |
|  482 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEmployeeDetailPage.qml` |
|  481 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksWorkspacePage.qml` |
|  450 | `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml` |
|  446 | `src/ui_qml/shell/qml/LoginWindow.qml` |
|  440 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioBottomPanel.qml` |
|  425 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminEntityDetailPage.qml` |
|  425 | `src/ui_qml/modules/project_management/qml/workspaces/register/panels/RegisterDetailPanel.qml` |
|  425 | `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspaceState.qml` |
|  424 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksTimeEntriesSection.qml` |
|  423 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminUserDetailPage.qml` |
|  421 | `src/ui_qml/platform/qml/workspaces/control/ControlWorkspacePage.qml` |
|  416 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminOrganizationDetailPage.qml` |
|  415 | `src/ui_qml/platform/qml/workspaces/admin/dialogs/AdminDialogHost.qml` |
|  405 | `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspacePage.qml` |
|  405 | `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectsImportDialog.qml` |
|  395 | `src/ui_qml/modules/project_management/qml/workspaces/projects/sections/ProjectsResourcesSection.qml` |
|  394 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/panels/TasksDetailPanel.qml` |
|  388 | `src/ui_qml/modules/project_management/qml/workspaces/resources/sections/ResourcesAvailabilitySection.qml` |
|  387 | `src/ui_qml/platform/qml/workspaces/admin/panels/AdminEntityDetailPanel.qml` |
|  380 | `src/ui_qml/modules/inventory_procurement/qml/workspaces/catalog/components/CatalogListPage.qml` |
|  370 | `src/ui_qml/modules/inventory_procurement/qml/workspaces/procurement/ProcurementWorkspacePage.qml` |
|  360 | `src/ui_qml/platform/qml/workspaces/admin/detail/AdminAccessDetailPage.qml` |
|  360 | `src/ui_qml/modules/project_management/qml/workspaces/portfolio/PortfolioWorkspacePage.qml` |
|  359 | `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksDialogHost.qml` |
|  352 | `src/ui_qml/platform/qml/workspaces/control/detail/ControlApprovalDetailPage.qml` |
|  352 | `src/ui_qml/platform/qml/Platform/Dialogs/PartyEditorDialog.qml` |

---

## Priority Tier 6 — Composition & Config

Wiring files. These grow naturally but signal architecture smell when very large.

| LOC | File |
|----:|------|
|  533 | `src/infra/composition/maintenance_registry.py` |
|  470 | `src/infra/composition/project_registry.py` |
|  457 | `src/infra/composition/app_container.py` |
|  438 | `src/api/desktop/platform/models/enterprise_calendar.py` |
|  407 | `src/infra/composition/platform_registry.py` |

---

## Priority Tier 7 — Tests

Large test files reduce test isolation and increase CI time. Target: split by scenario group.

| LOC | File |
|----:|------|
| 3389 | `src/tests/project_management/test_project_management_desktop_api.py` |
| 2483 | `src/tests/platform/test_qml_platform_presenters.py` |
| 2375 | `src/tests/project_management/test_qml_project_management_presenters.py` |
| 1089 | `src/tests/maintenance/test_maintenance_foundation.py` |
| 1004 | `src/tests/maintenance/test_maintenance_desktop_api.py` |
|  922 | `src/tests/maintenance/test_maintenance_persistence.py` |
|  784 | `src/tests/inventory_procurement/test_inventory_procurement_desktop_api.py` |
|  773 | `src/tests/platform/test_enterprise_calendar_foundation.py` |
|  755 | `src/tests/architecture/test_qml_architecture_guardrails.py` |
|  741 | `src/tests/inventory_procurement/test_qml_inventory_procurement_presenters.py` |
|  708 | `src/tests/architecture/test_architecture_guardrails.py` |
|  616 | `src/tests/project_management/test_enterprise_calendar_pm_integration.py` |
|  546 | `src/tests/inventory_procurement/test_inventory_procurement_purchasing.py` |
|  500 | `src/tests/maintenance/test_qml_maintenance_presenters.py` |
|  469 | `src/tests/test_exporters_configuration.py` |
|  460 | `src/tests/inventory_procurement/test_qml_inventory_procurement_dialog_hosts.py` |
|  431 | `src/tests/project_management/test_technical_math_reporting.py` |
|  424 | `src/tests/test_qml_shared_primitives.py` |
|  417 | `src/tests/project_management/test_enterprise_pm_foundation.py` |
|  406 | `src/tests/test_qml_domain_event_bridges.py` |
|  397 | `src/tests/maintenance/test_maintenance_preventive_foundation.py` |
|  389 | `src/tests/project_management/test_shared_collaboration_import_and_timesheets.py` |
|  383 | `src/tests/path_rewrites.py` |
|  378 | `src/tests/project_management/test_business_rules_and_edge_cases.py` |
|  361 | `src/tests/maintenance/test_maintenance_preventive_generation.py` |
|  355 | `src/tests/project_management/test_scheduling_enterprise_calendar_integration.py` |
|  355 | `src/tests/inventory_procurement/test_inventory_procurement_foundation.py` |

---

## Priority Tier 8 — Migration Files

Schema files. Rarely changed. Document them but do not refactor.

| LOC | File |
|----:|------|
|  357 | `src/infra/persistence/migrations/versions/n7o8p9q0r1s2_add_platform_enterprise_calendars.py` |
|  351 | `src/infra/persistence/migrations/versions/9d4e7f1a2b3c_expand_shared_master_metadata.py` |

---

## Quick Stats by Tier

| Tier | Files | Refactor approach |
|---|---|---|
| 1 — Application Services | 43 | Split by command/query, aggregate, or mixin |
| 2 — API / Desktop Layer | 17 | Split by workspace section, extract serializers |
| 3 — Controllers / Presenters | 19 | Extract sub-controllers, section presenters |
| 4 — Infrastructure | 20 | Split by aggregate root or bounded context |
| 5 — QML Workspace Files | 38 | Extract panels, sections, list pages |
| 6 — Composition / Config | 5 | Extract sub-registries per module |
| 7 — Tests | 27 | Split by scenario group |
| 8 — Migration Files | 2 | Document only — do not refactor |
| **Total** | **171** | |

---

## Top 10 Highest-Impact Splits

These 10 files alone account for the most technical debt by volume and domain impact:

1. `test_project_management_desktop_api.py` (3389) — split by workspace domain
2. `test_qml_platform_presenters.py` (2483) — split by admin section
3. `test_qml_project_management_presenters.py` (2375) — split by workspace domain
4. `maintenance/repositories/repository.py` (1489) — split by asset, WO, preventive, reliability
5. `maintenance/orm/models.py` (1282) — split by aggregate (asset, WO, preventive, reliability)
6. `maintenance/mappers/mapper.py` (1203) — split by aggregate root
7. `scheduling_workspace_controller.py` (1195) — split by CPM, baseline, leveling, calendar
8. `test_maintenance_foundation.py` (1089) — split by service group
9. `admin_console_controller.py` (1046) — split by admin section (sites, orgs, users, calendar)
10. `auth_service.py` (1025) — split by auth domain (sessions, tokens, permissions)
