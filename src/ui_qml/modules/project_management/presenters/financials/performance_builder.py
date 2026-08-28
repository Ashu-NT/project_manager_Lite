from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _date_label(value) -> str:
    return "Not available" if value is None else value.isoformat()


def _metric_collection(title: str, subtitle: str, metrics) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title=title,
        subtitle=subtitle,
        empty_state="No authoritative metrics are available.",
        items=tuple(
            FinancialsRecordViewModel(
                id=item.code,
                title=item.label,
                status_label=item.value_label,
                subtitle=item.supporting_text,
                supporting_text=(
                    "Unavailable" if item.availability != "available" else "Authoritative read"
                ),
                meta_text=item.availability.replace("_", " ").title(),
                can_primary_action=False,
                can_secondary_action=False,
                state={
                    "value": item.value,
                    "availability": item.availability,
                    "tone": item.tone,
                },
            )
            for item in metrics
        ),
        total=len(metrics),
    )


def build_evm_views(dto) -> dict[str, object]:
    basis = FinancialsDetailViewModel(
        id=dto.baseline_id,
        title="Earned Value Management",
        status_label=dto.availability.replace("_", " ").title(),
        subtitle=(
            dto.unavailable_reason
            or "Existing EVM authority isolated behind the Performance read boundary."
        ),
        description=dto.notes,
        empty_state=dto.unavailable_reason,
        fields=(
            FinancialsDetailFieldViewModel("As of", _date_label(dto.as_of_date)),
            FinancialsDetailFieldViewModel("Currency", dto.currency_code or "Not configured"),
            FinancialsDetailFieldViewModel("Baseline", dto.baseline_id or "Not approved"),
            FinancialsDetailFieldViewModel(
                "Budget revision",
                "Not approved" if dto.budget_revision is None else f"r{dto.budget_revision}",
            ),
            FinancialsDetailFieldViewModel(
                "Forecast revision",
                "Not approved" if dto.forecast_revision is None else f"r{dto.forecast_revision}",
                f"Forecast as of {_date_label(dto.forecast_as_of)}",
            ),
            FinancialsDetailFieldViewModel(
                "Calculation precision",
                "Current binary-float authority",
                "R6E owns the canonical Decimal replacement; this R6B read does not change formulas.",
            ),
        ),
        state={"availability": dto.availability},
    )
    return {
        "evm_basis": basis,
        "evm_metrics": _metric_collection(
            "EVM Metrics",
            "BAC/PV/EV/AC and existing derived metrics at the selected as-of date.",
            dto.metrics,
        ),
    }


def build_variance_views(dto) -> dict[str, object]:
    baseline_id = dto.selected_baseline_id
    return {
        "variance_metrics": _metric_collection(
            "Variance Measures",
            "Each measure carries its own formula identity and sign convention.",
            dto.metrics,
        ),
        "selected_baseline_id": baseline_id,
        "baseline_versions": FinancialsCollectionViewModel(
            title="Schedule Baseline Versions",
            subtitle="Stored plan-to-plan movement; this is distinct from EVM schedule variance.",
            empty_state="No approved schedule baselines exist for this project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.name,
                    status_label=item.status_label,
                    subtitle=f"Version {item.version} | Created {item.created_at_label}",
                    supporting_text=(
                        f"Approved {item.approved_at_label}"
                        if item.approved_at_label
                        else "Not approved"
                    ),
                    meta_text="Selected" if item.id == baseline_id else "",
                    state={"selected": item.id == baseline_id},
                )
                for item in dto.baselines
            ),
            total=len(dto.baselines),
        ),
        "baseline_variance": tuple(
            BaselineVarianceRowViewModel(
                task_id=item.task_id,
                task_name=item.task_name,
                start_variance_days=item.start_variance_days,
                finish_variance_days=item.finish_variance_days,
                cost_variance=item.cost_variance,
                cost_variance_label=item.cost_variance_label,
                tone=item.tone,
            )
            for item in dto.records
        ),
        "variance_basis": FinancialsDetailViewModel(
            id=baseline_id,
            title=dto.selected_baseline_label,
            status_label="Stored baseline comparison" if baseline_id else "",
            empty_state="Select a schedule baseline to review stored plan movement.",
            fields=(
                FinancialsDetailFieldViewModel("Selected baseline", dto.selected_baseline_label),
                FinancialsDetailFieldViewModel("Compared baseline", dto.compared_baseline_id or "No predecessor comparison"),
                FinancialsDetailFieldViewModel("As of", _date_label(dto.as_of_date)),
                FinancialsDetailFieldViewModel(
                    "Authority",
                    "Plan-to-plan schedule and planned-cost movement",
                    "This is baseline history, not actual-cost performance or EVM schedule variance.",
                ),
            ) if baseline_id else (),
        ),
    }


def build_cost_phasing_views(dto) -> dict[str, object]:
    return {
        "cost_phasing": FinancialsCollectionViewModel(
            title="Cost Phasing",
            subtitle="Bounded staged project costs. This is not cash receipts, payments, liquidity, AR, or AP.",
            empty_state="No staged cost facts exist in the selected range.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=row.period_key,
                    title=row.period_key,
                    status_label=row.forecast_label,
                    subtitle=f"Planned {row.planned_label} | Committed {row.committed_label}",
                    supporting_text=f"Posted actual {row.actual_label} | Exposure {row.exposure_label}",
                    meta_text=dto.granularity.title(),
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={
                        "planned": row.planned,
                        "committed": row.committed,
                        "actual": row.actual,
                        "forecast": row.forecast,
                        "exposure": row.exposure,
                    },
                )
                for row in dto.periods
            ),
            total=len(dto.periods),
        ),
        "cost_phasing_basis": FinancialsDetailViewModel(
            id=dto.project_id,
            title="Cost Phasing Read Basis",
            status_label=f"{dto.granularity.title()} range",
            fields=(
                FinancialsDetailFieldViewModel("Range", f"{_date_label(dto.date_from)} to {_date_label(dto.date_to)}"),
                FinancialsDetailFieldViewModel("Currency", dto.currency_code or "Not configured"),
                FinancialsDetailFieldViewModel("Budget revision", "Not approved" if dto.approved_budget_revision is None else f"r{dto.approved_budget_revision}"),
                FinancialsDetailFieldViewModel("Forecast revision", "Not approved" if dto.approved_forecast_revision is None else f"r{dto.approved_forecast_revision}"),
            ),
        ),
    }


def build_reports_views(dto) -> dict[str, object]:
    return {
        "report_basis": FinancialsDetailViewModel(
            id=dto.project_id,
            title="Project Finance Reports",
            status_label="Authoritative read basis",
            empty_state="No authorized Finance report basis is available.",
            fields=(
                FinancialsDetailFieldViewModel("As of", _date_label(dto.as_of_date)),
                FinancialsDetailFieldViewModel("Currency", dto.currency_code or "Not configured"),
                FinancialsDetailFieldViewModel("Budget revision", "Not approved" if dto.budget_revision is None else f"r{dto.budget_revision}"),
                FinancialsDetailFieldViewModel("Forecast revision", "Not approved" if dto.forecast_revision is None else f"r{dto.forecast_revision}"),
            ),
        ),
        "report_definitions": FinancialsCollectionViewModel(
            title="Available Reports",
            subtitle="Export adapters consume authoritative reads and do not own financial formulas.",
            empty_state="No reports are authorized.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.report_code,
                    title=item.display_name,
                    status_label=" / ".join(value.upper() for value in item.formats),
                    subtitle=item.authority_label,
                    supporting_text="report.view to inspect; report.export plus source permissions to export",
                    meta_text="Read only",
                    can_primary_action=False,
                    can_secondary_action=False,
                )
                for item in dto.definitions
            ),
            total=len(dto.definitions),
        ),
    }


__all__ = ["build_cost_phasing_views", "build_evm_views", "build_reports_views", "build_variance_views"]
