from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters import (
    PlatformAdminWorkspacePresenter,
    PlatformControlQueuePresenter,
    PlatformControlWorkspacePresenter,
    PlatformSettingsCatalogPresenter,
    PlatformSettingsWorkspacePresenter,
)


def serialize_workspace_overview(overview) -> dict[str, object]:
    return {
        "title": overview.title,
        "subtitle": overview.subtitle,
        "statusLabel": overview.status_label,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in overview.metrics
        ],
        "sections": [
            {
                "title": section.title,
                "emptyState": section.empty_state,
                "rows": [
                    {
                        "label": row.label,
                        "value": row.value,
                        "supportingText": row.supporting_text,
                    }
                    for row in section.rows
                ],
            }
            for section in overview.sections
        ],
    }


def serialize_action_list(list_view_model) -> dict[str, object]:
    return {
        "title": list_view_model.title,
        "subtitle": list_view_model.subtitle,
        "emptyState": list_view_model.empty_state,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "statusLabel": item.status_label,
                "subtitle": item.subtitle,
                "supportingText": item.supporting_text,
                "metaText": item.meta_text,
                "canPrimaryAction": item.can_primary_action,
                "canSecondaryAction": item.can_secondary_action,
                "state": dict(item.state),
            }
            for item in list_view_model.items
        ],
    }


def serialize_operation_result(
    result,
    *,
    success_message: str,
) -> dict[str, object]:
    if result is not None and getattr(result, "ok", False):
        return {
            "ok": True,
            "category": "",
            "code": "",
            "message": success_message,
        }
    error = getattr(result, "error", None) if result is not None else None
    return {
        "ok": False,
        "category": getattr(error, "category", "domain"),
        "code": getattr(error, "code", "operation_failed"),
        "message": getattr(error, "message", "The platform QML action did not complete."),
    }


class _BasePlatformWorkspaceController(QObject):
    overviewChanged = Signal()
    isLoadingChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    feedbackMessageChanged = Signal()
    emptyStateChanged = Signal()
    operationResultChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "statusLabel": "", "metrics": [], "sections": []}
        self._is_loading = False
        self._is_busy = False
        self._error_message = ""
        self._feedback_message = ""
        self._empty_state = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(str, notify=feedbackMessageChanged)
    def feedbackMessage(self) -> str:
        return self._feedback_message

    @Property(str, notify=emptyStateChanged)
    def emptyState(self) -> str:
        return self._empty_state

    @Property("QVariantMap", notify=operationResultChanged)
    def operationResult(self) -> dict[str, object]:
        return self._operation_result

    @Slot()
    def clearMessages(self) -> None:
        self._set_error_message("")
        self._set_feedback_message("")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_is_loading(self, value: bool) -> None:
        if value == self._is_loading:
            return
        self._is_loading = value
        self.isLoadingChanged.emit()

    def _set_is_busy(self, value: bool) -> None:
        if value == self._is_busy:
            return
        self._is_busy = value
        self.isBusyChanged.emit()

    def _set_error_message(self, value: str) -> None:
        if value == self._error_message:
            return
        self._error_message = value
        self.errorMessageChanged.emit()

    def _set_feedback_message(self, value: str) -> None:
        if value == self._feedback_message:
            return
        self._feedback_message = value
        self.feedbackMessageChanged.emit()

    def _set_empty_state(self, value: str) -> None:
        if value == self._empty_state:
            return
        self._empty_state = value
        self.emptyStateChanged.emit()

    def _set_operation_result(self, value: dict[str, object]) -> None:
        if value == self._operation_result:
            return
        self._operation_result = value
        self.operationResultChanged.emit()


class PlatformAdminWorkspaceController(_BasePlatformWorkspaceController):
    def __init__(
        self,
        *,
        presenter: PlatformAdminWorkspacePresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        overview = serialize_workspace_overview(self._presenter.build_overview())
        self._set_overview(overview)
        has_content = bool(overview.get("metrics") or overview.get("sections"))
        self._set_empty_state("" if has_content else "No platform administration data is available yet.")
        self._set_is_loading(False)


class PlatformControlWorkspaceController(_BasePlatformWorkspaceController):
    approvalQueueChanged = Signal()
    auditFeedChanged = Signal()

    def __init__(
        self,
        *,
        overview_presenter: PlatformControlWorkspacePresenter,
        queue_presenter: PlatformControlQueuePresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._queue_presenter = queue_presenter
        self._approval_queue: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._audit_feed: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self.refresh()

    @Property("QVariantMap", notify=approvalQueueChanged)
    def approvalQueue(self) -> dict[str, object]:
        return self._approval_queue

    @Property("QVariantMap", notify=auditFeedChanged)
    def auditFeed(self) -> dict[str, object]:
        return self._audit_feed

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))
        self._set_approval_queue(serialize_action_list(self._queue_presenter.build_approval_queue()))
        self._set_audit_feed(serialize_action_list(self._queue_presenter.build_audit_feed()))
        has_items = bool(self._approval_queue.get("items") or self._audit_feed.get("items"))
        self._set_empty_state("" if has_items else str(self._approval_queue.get("emptyState") or self._audit_feed.get("emptyState") or ""))
        self._set_is_loading(False)

    @Slot(str)
    def approveRequest(self, request_id: str) -> None:
        self._apply_request_action(
            request_id=request_id,
            operation=self._queue_presenter.approve_request,
            success_message="Approval request approved and applied.",
            new_status="Approved",
        )

    @Slot(str)
    def rejectRequest(self, request_id: str) -> None:
        self._apply_request_action(
            request_id=request_id,
            operation=self._queue_presenter.reject_request,
            success_message="Approval request rejected.",
            new_status="Rejected",
        )

    def _apply_request_action(
        self,
        *,
        request_id: str,
        operation,
        success_message: str,
        new_status: str,
    ) -> None:
        normalized_id = request_id.strip()
        if not normalized_id:
            return
        self._set_is_busy(True)
        self._set_error_message("")
        result = operation(normalized_id)
        payload = serialize_operation_result(result, success_message=success_message)
        self._set_operation_result(payload)
        if payload["ok"]:
            self._set_feedback_message(str(payload["message"]))
            self._apply_request_update(request_id=normalized_id, new_status=new_status)
        else:
            self._set_feedback_message("")
            self._set_error_message(str(payload["message"]))
        self._set_is_busy(False)

    def _apply_request_update(self, *, request_id: str, new_status: str) -> None:
        items = [dict(item) for item in self._approval_queue.get("items", [])]
        updated = False
        for item in items:
            if item.get("id") != request_id:
                continue
            item["statusLabel"] = new_status
            item["canPrimaryAction"] = False
            item["canSecondaryAction"] = False
            state = dict(item.get("state") or {})
            state["status"] = new_status.lower()
            item["state"] = state
            updated = True
            break
        if not updated:
            self.refresh()
            return
        approval_queue = dict(self._approval_queue)
        approval_queue["items"] = items
        self._set_approval_queue(approval_queue)
        self._update_control_metrics()
        self._set_empty_state("" if items or self._audit_feed.get("items") else str(self._approval_queue.get("emptyState") or ""))

    def _update_control_metrics(self) -> None:
        items = self._approval_queue.get("items", [])
        pending_count = sum(1 for item in items if str((item.get("state") or {}).get("status", "")).lower() == "pending")
        approved_count = sum(1 for item in items if str((item.get("state") or {}).get("status", "")).lower() == "approved")
        rejected_count = sum(1 for item in items if str((item.get("state") or {}).get("status", "")).lower() == "rejected")
        metrics = [
            {
                "label": "Pending approvals",
                "value": str(pending_count),
                "supportingText": "Requests awaiting decision",
            },
            {
                "label": "Approved",
                "value": str(approved_count),
                "supportingText": "Requests already applied",
            },
            {
                "label": "Rejected",
                "value": str(rejected_count),
                "supportingText": "Requests closed without apply",
            },
            {
                "label": "Audit entries",
                "value": str(len(self._audit_feed.get("items", []))),
                "supportingText": "Recent governance and activity trail",
            },
        ]
        overview = dict(self._overview)
        overview["metrics"] = metrics
        self._set_overview(overview)

    def _set_approval_queue(self, approval_queue: dict[str, object]) -> None:
        if approval_queue == self._approval_queue:
            return
        self._approval_queue = approval_queue
        self.approvalQueueChanged.emit()

    def _set_audit_feed(self, audit_feed: dict[str, object]) -> None:
        if audit_feed == self._audit_feed:
            return
        self._audit_feed = audit_feed
        self.auditFeedChanged.emit()


class PlatformSettingsWorkspaceController(_BasePlatformWorkspaceController):
    moduleEntitlementsChanged = Signal()
    organizationProfilesChanged = Signal()

    def __init__(
        self,
        *,
        overview_presenter: PlatformSettingsWorkspacePresenter,
        catalog_presenter: PlatformSettingsCatalogPresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._overview_presenter = overview_presenter
        self._catalog_presenter = catalog_presenter
        self._module_entitlements: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._organization_profiles: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self.refresh()

    @Property("QVariantMap", notify=moduleEntitlementsChanged)
    def moduleEntitlements(self) -> dict[str, object]:
        return self._module_entitlements

    @Property("QVariantMap", notify=organizationProfilesChanged)
    def organizationProfiles(self) -> dict[str, object]:
        return self._organization_profiles

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        self._set_overview(serialize_workspace_overview(self._overview_presenter.build_overview()))
        self._set_module_entitlements(serialize_action_list(self._catalog_presenter.build_module_entitlements()))
        self._set_organization_profiles(serialize_action_list(self._catalog_presenter.build_organization_profiles()))
        has_items = bool(self._module_entitlements.get("items") or self._organization_profiles.get("items"))
        self._set_empty_state("" if has_items else str(self._module_entitlements.get("emptyState") or self._organization_profiles.get("emptyState") or ""))
        self._set_is_loading(False)

    @Slot(str)
    def toggleModuleLicensed(self, module_code: str) -> None:
        self._apply_entitlement_action(
            module_code=module_code,
            operation=self._catalog_presenter.toggle_module_license,
            success_message="Module license state updated.",
        )

    @Slot(str)
    def toggleModuleEnabled(self, module_code: str) -> None:
        self._apply_entitlement_action(
            module_code=module_code,
            operation=self._catalog_presenter.toggle_module_enabled,
            success_message="Module runtime state updated.",
        )

    def _apply_entitlement_action(
        self,
        *,
        module_code: str,
        operation,
        success_message: str,
    ) -> None:
        normalized_code = module_code.strip()
        if not normalized_code:
            return
        self._set_is_busy(True)
        self._set_error_message("")
        result = operation(normalized_code)
        payload = serialize_operation_result(result, success_message=success_message)
        self._set_operation_result(payload)
        if payload["ok"] and getattr(result, "data", None) is not None:
            self._set_feedback_message(str(payload["message"]))
            self._apply_entitlement_update(result.data)
        else:
            self._set_feedback_message("")
            self._set_error_message(str(payload["message"]))
        self._set_is_busy(False)

    def _apply_entitlement_update(self, entitlement) -> None:
        items = [dict(item) for item in self._module_entitlements.get("items", [])]
        updated = False
        for index, item in enumerate(items):
            if item.get("id") != entitlement.module_code:
                continue
            items[index] = self._serialize_entitlement_item(entitlement)
            updated = True
            break
        if not updated:
            self.refresh()
            return
        module_entitlements = dict(self._module_entitlements)
        module_entitlements["items"] = items
        self._set_module_entitlements(module_entitlements)
        self._update_settings_metrics()

    def _update_settings_metrics(self) -> None:
        items = self._module_entitlements.get("items", [])
        licensed_count = sum(1 for item in items if bool((item.get("state") or {}).get("licensed")))
        enabled_count = sum(1 for item in items if bool((item.get("state") or {}).get("enabled")))
        planned_count = sum(1 for item in items if bool((item.get("state") or {}).get("planned")))
        metrics = [
            {
                "label": "Licensed modules",
                "value": str(licensed_count),
                "supportingText": "Currently licensed",
            },
            {
                "label": "Enabled modules",
                "value": str(enabled_count),
                "supportingText": "Runtime active",
            },
            {
                "label": "Planned modules",
                "value": str(planned_count),
                "supportingText": "Not yet enabled",
            },
            {
                "label": "Organizations",
                "value": str(len(self._organization_profiles.get("items", []))),
                "supportingText": "Install profiles",
            },
        ]
        overview = dict(self._overview)
        overview["metrics"] = metrics
        self._set_overview(overview)

    @staticmethod
    def _serialize_entitlement_item(entitlement) -> dict[str, Any]:
        return {
            "id": entitlement.module_code,
            "title": entitlement.label,
            "statusLabel": entitlement.lifecycle_label,
            "subtitle": (
                f"{entitlement.stage.title()} | "
                f"{'Licensed' if entitlement.licensed else 'Unlicensed'} | "
                f"{'Enabled' if entitlement.enabled else 'Disabled'}"
            ),
            "supportingText": entitlement.module.description,
            "metaText": (
                f"Runtime: {'Yes' if entitlement.runtime_enabled else 'No'} | "
                f"Capabilities: {', '.join(entitlement.module.primary_capabilities) or '-'}"
            ),
            "canPrimaryAction": not entitlement.planned,
            "canSecondaryAction": (
                not entitlement.planned
                and entitlement.licensed
                and not (
                    not entitlement.runtime_enabled
                    and entitlement.lifecycle_status in {"suspended", "expired"}
                )
            ),
            "state": {
                "licensed": entitlement.licensed,
                "enabled": entitlement.enabled,
                "planned": entitlement.planned,
                "runtimeEnabled": entitlement.runtime_enabled,
                "lifecycleStatus": entitlement.lifecycle_status,
            },
        }

    def _set_module_entitlements(self, module_entitlements: dict[str, object]) -> None:
        if module_entitlements == self._module_entitlements:
            return
        self._module_entitlements = module_entitlements
        self.moduleEntitlementsChanged.emit()

    def _set_organization_profiles(self, organization_profiles: dict[str, object]) -> None:
        if organization_profiles == self._organization_profiles:
            return
        self._organization_profiles = organization_profiles
        self.organizationProfilesChanged.emit()


__all__ = [
    "PlatformAdminWorkspaceController",
    "PlatformControlWorkspaceController",
    "PlatformSettingsWorkspaceController",
    "serialize_action_list",
    "serialize_operation_result",
    "serialize_workspace_overview",
]
