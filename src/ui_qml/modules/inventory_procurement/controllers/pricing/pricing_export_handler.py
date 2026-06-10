from __future__ import annotations


def _run_export_action(ctrl, operation, *, success_prefix: str) -> dict[str, object]:
    ctrl._set_is_busy(True)
    ctrl._set_error_message("")
    try:
        output_path = operation()
    except Exception as exc:
        ctrl._set_feedback_message("")
        ctrl._set_error_message(str(exc))
        payload = {"ok": False, "message": str(exc)}
    else:
        message = f"{success_prefix} {output_path}"
        ctrl._set_feedback_message(message)
        payload = {"ok": True, "message": message, "path": output_path}
    finally:
        ctrl._set_is_busy(False)
    return payload


def export_stock_status_csv(ctrl, output_path: str) -> dict[str, object]:
    return _run_export_action(
        ctrl,
        lambda: ctrl._pricing_workspace_presenter.export_stock_status_csv(
            output_path,
            site_filter=ctrl._selected_site_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
        ),
        success_prefix="Stock CSV exported to",
    )


def export_stock_status_excel(ctrl, output_path: str) -> dict[str, object]:
    return _run_export_action(
        ctrl,
        lambda: ctrl._pricing_workspace_presenter.export_stock_status_excel(
            output_path,
            site_filter=ctrl._selected_site_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
        ),
        success_prefix="Stock Excel exported to",
    )


def export_procurement_overview_csv(ctrl, output_path: str) -> dict[str, object]:
    return _run_export_action(
        ctrl,
        lambda: ctrl._pricing_workspace_presenter.export_procurement_overview_csv(
            output_path,
            site_filter=ctrl._selected_site_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
            supplier_filter=ctrl._selected_supplier_filter,
            limit_filter=ctrl._selected_limit_filter,
        ),
        success_prefix="Procurement CSV exported to",
    )


def export_procurement_overview_excel(ctrl, output_path: str) -> dict[str, object]:
    return _run_export_action(
        ctrl,
        lambda: ctrl._pricing_workspace_presenter.export_procurement_overview_excel(
            output_path,
            site_filter=ctrl._selected_site_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
            supplier_filter=ctrl._selected_supplier_filter,
            limit_filter=ctrl._selected_limit_filter,
        ),
        success_prefix="Procurement Excel exported to",
    )
