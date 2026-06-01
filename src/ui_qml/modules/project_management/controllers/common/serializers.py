from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationContextViewModel,
    CollaborationDetailViewModel,
    CollaborationOverviewViewModel,
    CollaborationPanelTabViewModel,
    CollaborationRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardActivityFeedViewModel,
    ProjectDashboardChartViewModel,
    ProjectDashboardHealthCardViewModel,
    ProjectDashboardOverviewViewModel,
    ProjectDashboardOperationalTableViewModel,
    ProjectDashboardPanelViewModel,
    ProjectDashboardSectionViewModel,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsCollectionViewModel,
    FinancialsCommitmentSummaryViewModel,
    FinancialsDetailViewModel,
    FinancialsForecastViewModel,
    FinancialsOverviewViewModel,
    FinancialsRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioCollectionViewModel,
    PortfolioOverviewViewModel,
    PortfolioRecordViewModel,
    PortfolioSummaryViewModel,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogOverviewViewModel,
    ProjectDetailViewModel,
    ProjectRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceAvailabilityViewModel,
    ResourceCatalogOverviewViewModel,
    ResourceCertificationViewModel,
    ResourceDetailViewModel,
    ResourceEmployeeOptionViewModel,
    ResourceRecordViewModel,
    ResourceSkillViewModel,
)
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterCollectionViewModel,
    RegisterDetailViewModel,
    RegisterOverviewViewModel,
    RegisterRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingBaselineCompareViewModel,
    SchedulingCalendarViewModel,
    SchedulingCollectionViewModel,
    SchedulingDetailViewModel,
    SchedulingOverviewViewModel,
    SchedulingRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogOverviewViewModel,
    TaskDetailViewModel,
    TaskExecutionCollectionViewModel,
    TaskRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetCollectionViewModel,
    TimesheetDetailViewModel,
    TimesheetOverviewViewModel,
    TimesheetRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.workspace import (
    ProjectManagementWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: ProjectManagementWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }


def serialize_collaboration_overview_view_model(
    view_model: CollaborationOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_collaboration_record_view_models(
    view_models: tuple[CollaborationRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "routeId": str(view_model.state.get("routeId", "")),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_collaboration_collection_view_model(
    view_model: CollaborationCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_collaboration_record_view_models(view_model.items),
    }


def serialize_collaboration_context_view_model(
    view_model: CollaborationContextViewModel,
) -> dict[str, object]:
    return {
        "projectOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.project_options
        ],
        "teamOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.team_options
        ],
        "periodOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.period_options
        ],
        "unreadOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.unread_options
        ],
    }


def serialize_collaboration_panel_tab_view_models(
    view_models: tuple[CollaborationPanelTabViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "label": view_model.label,
            "count": view_model.count,
        }
        for view_model in view_models
    ]


def serialize_collaboration_detail_view_model(
    view_model: CollaborationDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "state": dict(view_model.state),
        "fields": [
            {
                "label": field.label,
                "value": field.value,
            }
            for field in view_model.fields
        ],
        "activity": serialize_collaboration_collection_view_model(view_model.activity),
        "relatedItems": serialize_collaboration_collection_view_model(
            view_model.related_items
        ),
        "audit": serialize_collaboration_collection_view_model(view_model.audit),
    }


def serialize_dashboard_overview_view_model(
    view_model: ProjectDashboardOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_selector_options(view_models) -> list[dict[str, str]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
        }
        for view_model in view_models
    ]


def serialize_dashboard_section_view_models(view_models) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "statusLabel": item.status_label,
                    "subtitle": item.subtitle,
                    "supportingText": item.supporting_text,
                    "metaText": item.meta_text,
                    "state": dict(item.state),
                }
                for item in view_model.items
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_health_card_view_models(
    view_models: tuple[ProjectDashboardHealthCardViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "metricValue": view_model.metric_value,
            "metricLabel": view_model.metric_label,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "tone": view_model.tone,
            "routeId": view_model.route_id,
        }
        for view_model in view_models
    ]


def serialize_dashboard_operational_tab_view_models(view_models) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "label": view_model.label,
            "count": view_model.count,
            "routeId": view_model.route_id,
        }
        for view_model in view_models
    ]


def serialize_dashboard_operational_table_view_models(
    view_models: tuple[ProjectDashboardOperationalTableViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "columns": [
                {
                    "key": column.key,
                    "label": column.label,
                    "flex": column.flex,
                    "minWidth": column.min_width,
                    "sortable": column.sortable,
                    "visible": column.visible,
                    "type": column.column_type,
                }
                for column in view_model.columns
            ],
            "rows": [
                {
                    "id": row.id,
                    **dict(row.values),
                    "routeId": row.route_id,
                    "state": dict(row.state),
                }
                for row in view_model.rows
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_activity_feed_view_model(
    view_model: ProjectDashboardActivityFeedViewModel | None,
) -> dict[str, object]:
    if view_model is None:
        return {
            "title": "Recent Activity",
            "subtitle": "",
            "emptyState": "No recent activity is available yet.",
            "items": [],
        }
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "statusLabel": item.status_label,
                "metaText": item.meta_text,
                "routeId": item.route_id,
                "state": dict(item.state),
            }
            for item in view_model.items
        ],
    }


def serialize_dashboard_panel_view_models(
    view_models: tuple[ProjectDashboardPanelViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "hint": view_model.hint,
            "emptyState": view_model.empty_state,
            "rows": [
                {
                    "label": row.label,
                    "value": row.value,
                    "supportingText": row.supporting_text,
                    "tone": row.tone,
                }
                for row in view_model.rows
            ],
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.metrics
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_chart_view_models(
    view_models: tuple[ProjectDashboardChartViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "chartType": view_model.chart_type,
            "emptyState": view_model.empty_state,
            "points": [
                {
                    "label": point.label,
                    "value": point.value,
                    "valueLabel": point.value_label,
                    "supportingText": point.supporting_text,
                    "targetValue": point.target_value,
                    "tone": point.tone,
                }
                for point in view_model.points
            ],
        }
        for view_model in view_models
    ]


def serialize_project_catalog_overview_view_model(
    view_model: ProjectCatalogOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_financials_overview_view_model(
    view_model: FinancialsOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_financials_record_view_models(
    view_models: tuple[FinancialsRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "costCode": str(view_model.state.get("costCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "taskName": str(view_model.state.get("taskName", "") or ""),
            "plannedAmountLabel": str(view_model.state.get("plannedAmountLabel", "") or ""),
            "forecastAmountLabel": str(view_model.state.get("forecastAmountLabel", "") or ""),
            "committedAmountLabel": str(view_model.state.get("committedAmountLabel", "") or ""),
            "actualAmountLabel": str(view_model.state.get("actualAmountLabel", "") or ""),
            "commitmentStatusLabel": str(view_model.state.get("commitmentStatusLabel", "") or ""),
            "incurredDateLabel": str(view_model.state.get("incurredDateLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_financials_forecast_view_model(
    vm: FinancialsForecastViewModel,
) -> dict[str, object]:
    return {
        "method": vm.method,
        "methodLabel": vm.method_label,
        "bacLabel": vm.bac_label,
        "acLabel": vm.ac_label,
        "evLabel": vm.ev_label,
        "etcLabel": vm.etc_label,
        "eacLabel": vm.eac_label,
        "vacLabel": vm.vac_label,
        "cpiLabel": vm.cpi_label,
        "isOverBudget": vm.is_over_budget,
        "exceedsThreshold": vm.exceeds_threshold,
        "thresholdPercent": vm.threshold_percent,
        "alertMessage": vm.alert_message,
        "metrics": [
            {"label": m.label, "value": m.value, "colorHint": m.color_hint}
            for m in vm.metrics
        ],
    }


def serialize_financials_commitment_summary_view_model(
    vm: FinancialsCommitmentSummaryViewModel,
) -> dict[str, object]:
    return {
        "plannedLabel": vm.planned_label,
        "uncommittedLabel": vm.uncommitted_label,
        "committedLabel": vm.committed_label,
        "invoicedLabel": vm.invoiced_label,
        "paidLabel": vm.paid_label,
        "exposureLabel": vm.exposure_label,
        "commitmentRatePct": vm.commitment_rate_pct,
    }


def serialize_financials_baseline_variance_view_models(
    rows: tuple,
) -> list[dict[str, object]]:
    return [
        {
            "taskId": row.task_id,
            "taskName": row.task_name,
            "startVarianceDays": row.start_variance_days,
            "finishVarianceDays": row.finish_variance_days,
            "costVariance": row.cost_variance,
            "costVarianceLabel": row.cost_variance_label,
            "tone": row.tone,
        }
        for row in rows
    ]


def serialize_financials_collection_view_model(
    view_model: FinancialsCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_financials_record_view_models(view_model.items),
    }


def serialize_financials_detail_view_model(
    view_model: FinancialsDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_portfolio_overview_view_model(
    view_model: PortfolioOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_portfolio_record_view_models(
    view_models: tuple[PortfolioRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_portfolio_collection_view_model(
    view_model: PortfolioCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_portfolio_record_view_models(view_model.items),
    }


def serialize_portfolio_summary_view_model(
    view_model: PortfolioSummaryViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
    }


def serialize_project_record_view_models(
    view_models: tuple[ProjectRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "projectCode": str(view_model.state.get("projectCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "clientName": str(view_model.state.get("clientName", "") or ""),
            "clientContact": str(view_model.state.get("clientContact", "") or ""),
            "startDateLabel": str(view_model.state.get("startDateLabel", "") or ""),
            "endDateLabel": str(view_model.state.get("endDateLabel", "") or ""),
            "plannedBudgetLabel": str(view_model.state.get("plannedBudgetLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_project_detail_view_model(
    view_model: ProjectDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_resource_catalog_overview_view_model(
    view_model: ResourceCatalogOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_resource_employee_option_view_models(
    view_models: tuple[ResourceEmployeeOptionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
            "name": view_model.name,
            "title": view_model.title,
            "contact": view_model.contact,
            "context": view_model.context,
            "isActive": view_model.is_active,
        }
        for view_model in view_models
    ]


def serialize_resource_record_view_models(
    view_models: tuple[ResourceRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "resourceCode": str(view_model.state.get("resourceCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "role": str(view_model.state.get("role", "") or ""),
            "workerTypeLabel": str(view_model.state.get("workerTypeLabel", "") or ""),
            "costTypeLabel": str(view_model.state.get("costTypeLabel", "") or ""),
            "hourlyRateLabel": str(view_model.state.get("hourlyRateLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "utilizationValue": {
                "value": float(view_model.state.get("capacityPercent", "0") or "0") / 100.0,
                "label": view_model.state.get("capacityLabel", "—"),
            },
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_resource_skill_view_models(
    view_models: tuple[ResourceSkillViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": vm.id,
            "title": vm.skill_name or vm.skill_code,
            "subtitle": vm.skill_code,
            "statusLabel": vm.proficiency_label,
            "metaText": vm.notes or "",
            "skillCode": vm.skill_code,
            "skillName": vm.skill_name,
            "proficiency": vm.proficiency,
            "proficiencyLabel": vm.proficiency_label,
            "notes": vm.notes,
        }
        for vm in view_models
    ]


def serialize_resource_certification_view_models(
    view_models: tuple[ResourceCertificationViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": vm.id,
            "title": vm.certification_name or vm.certification_code,
            "subtitle": vm.certification_code,
            "statusLabel": vm.cert_status,
            "metaText": vm.expiry_date or "",
            "certificationCode": vm.certification_code,
            "certificationName": vm.certification_name,
            "issuedDate": vm.issued_date or "",
            "expiryDate": vm.expiry_date or "",
            "issuingBody": vm.issuing_body,
            "notes": vm.notes,
            "certStatus": vm.cert_status,
            "certStatusLabel": vm.cert_status_label,
        }
        for vm in view_models
    ]


def serialize_resource_availability_view_model(
    vm: ResourceAvailabilityViewModel,
) -> dict[str, object]:
    return {
        "resourceId": vm.resource_id,
        "peakLoadPercent": vm.peak_load_percent,
        "averageLoadPercent": vm.average_load_percent,
        "overloadedDays": vm.overloaded_days,
        "availableDays": vm.available_days,
        "isAvailable": vm.is_available,
        "fromDateLabel": vm.from_date_label,
        "toDateLabel": vm.to_date_label,
        "days": [
            {
                "dateLabel": d.date_label,
                "allocationPercent": d.allocation_percent,
                "allocationLabel": d.allocation_label,
                "overloaded": d.overloaded,
            }
            for d in vm.days
        ],
    }


def serialize_resource_detail_view_model(
    view_model: ResourceDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_register_overview_view_model(
    view_model: RegisterOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_register_record_view_models(
    view_models: tuple[RegisterRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "entryCode": str(view_model.state.get("entryCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "ownerName": str(view_model.state.get("ownerName", "")),
            "dueDateLabel": str(view_model.state.get("dueDateLabel", "")),
            "projectName": str(view_model.state.get("projectName", "") or ""),
            "typeLabel": str(view_model.state.get("typeLabel", "") or ""),
            "entryStatus": str(view_model.state.get("statusLabel", "") or ""),
            "severityLabel": str(view_model.state.get("severityLabel", "") or ""),
            "severityValue": {
                "value": float(view_model.state.get("severityScore", "0") or "0") / 100.0,
                "label": view_model.state.get("severityLabel", "—"),
            },
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_register_collection_view_model(
    view_model: RegisterCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_register_record_view_models(view_model.items),
    }


def serialize_register_detail_view_model(
    view_model: RegisterDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_task_catalog_overview_view_model(
    view_model: TaskCatalogOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_task_record_view_models(
    view_models: tuple[TaskRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "projectName": str(view_model.state.get("projectName", "") or ""),
            "startDateLabel": str(view_model.state.get("startDateLabel", "") or ""),
            "endDateLabel": str(view_model.state.get("endDateLabel", "") or ""),
            "priorityLabel": str(view_model.state.get("priorityLabel", "") or ""),
            "deadlineLabel": str(view_model.state.get("deadlineLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "progressValue": {
                "value": float(view_model.state.get("percentComplete", "0") or "0") / 100.0,
                "label": view_model.state.get("percentCompleteLabel", "0%"),
            },
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_task_collection_view_model(
    view_model: TaskExecutionCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_task_record_view_models(view_model.items),
    }


def serialize_task_detail_view_model(
    view_model: TaskDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_timesheet_overview_view_model(
    view_model: TimesheetOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_timesheet_record_view_models(
    view_models: tuple[TimesheetRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_timesheet_collection_view_model(
    view_model: TimesheetCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_timesheet_record_view_models(view_model.items),
    }


def serialize_timesheet_detail_view_model(
    view_model: TimesheetDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


def serialize_scheduling_overview_view_model(
    view_model: SchedulingOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_scheduling_record_view_models(
    view_models: tuple[SchedulingRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_scheduling_collection_view_model(
    view_model: SchedulingCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_scheduling_record_view_models(view_model.items),
    }


def serialize_scheduling_calendar_view_model(
    view_model: SchedulingCalendarViewModel,
) -> dict[str, object]:
    return {
        "summaryText": view_model.summary_text,
        "workingDays": [
            {
                "index": option.index,
                "label": option.label,
                "checked": option.checked,
            }
            for option in view_model.working_day_options
        ],
        "hoursPerDay": view_model.hours_per_day,
        "holidays": serialize_scheduling_record_view_models(view_model.holidays),
        "emptyState": view_model.empty_state,
    }


def serialize_scheduling_baselines_view_model(
    view_model: SchedulingBaselineCompareViewModel,
) -> dict[str, object]:
    return {
        "options": serialize_selector_options(view_model.options),
        "selectedBaselineAId": view_model.selected_baseline_a_id,
        "selectedBaselineBId": view_model.selected_baseline_b_id,
        "includeUnchanged": view_model.include_unchanged,
        "summaryText": view_model.summary_text,
        "rows": serialize_scheduling_record_view_models(view_model.rows),
        "emptyState": view_model.empty_state,
    }


def serialize_scheduling_detail_view_model(
    view_model: SchedulingDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


__all__ = [
    "serialize_collaboration_collection_view_model",
    "serialize_collaboration_context_view_model",
    "serialize_collaboration_detail_view_model",
    "serialize_collaboration_overview_view_model",
    "serialize_collaboration_panel_tab_view_models",
    "serialize_collaboration_record_view_models",
    "serialize_dashboard_activity_feed_view_model",
    "serialize_dashboard_chart_view_models",
    "serialize_dashboard_health_card_view_models",
    "serialize_dashboard_overview_view_model",
    "serialize_dashboard_operational_tab_view_models",
    "serialize_dashboard_operational_table_view_models",
    "serialize_dashboard_panel_view_models",
    "serialize_dashboard_section_view_models",
    "serialize_financials_baseline_variance_view_models",
    "serialize_financials_collection_view_model",
    "serialize_financials_commitment_summary_view_model",
    "serialize_financials_detail_view_model",
    "serialize_financials_forecast_view_model",
    "serialize_financials_overview_view_model",
    "serialize_financials_record_view_models",
    "serialize_portfolio_collection_view_model",
    "serialize_portfolio_overview_view_model",
    "serialize_portfolio_record_view_models",
    "serialize_portfolio_summary_view_model",
    "serialize_project_catalog_overview_view_model",
    "serialize_project_detail_view_model",
    "serialize_project_record_view_models",
    "serialize_register_collection_view_model",
    "serialize_register_detail_view_model",
    "serialize_register_overview_view_model",
    "serialize_register_record_view_models",
    "serialize_resource_catalog_overview_view_model",
    "serialize_resource_certification_view_models",
    "serialize_resource_availability_view_model",
    "serialize_resource_detail_view_model",
    "serialize_resource_employee_option_view_models",
    "serialize_resource_record_view_models",
    "serialize_resource_skill_view_models",
    "serialize_scheduling_baselines_view_model",
    "serialize_scheduling_calendar_view_model",
    "serialize_scheduling_collection_view_model",
    "serialize_scheduling_detail_view_model",
    "serialize_scheduling_overview_view_model",
    "serialize_scheduling_record_view_models",
    "serialize_selector_options",
    "serialize_task_catalog_overview_view_model",
    "serialize_task_collection_view_model",
    "serialize_task_detail_view_model",
    "serialize_task_record_view_models",
    "serialize_timesheet_collection_view_model",
    "serialize_timesheet_detail_view_model",
    "serialize_timesheet_overview_view_model",
    "serialize_timesheet_record_view_models",
    "serialize_workspace_view_model",
]
