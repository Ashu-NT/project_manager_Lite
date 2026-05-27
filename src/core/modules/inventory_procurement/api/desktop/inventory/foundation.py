from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.inventory_procurement.api.desktop._support import (
    format_amount,
    format_date,
    format_enum_label,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryCycleCountCompleteCommand,
    InventoryCycleCountCreateCommand,
    InventoryCycleCountDesktopDto,
    InventoryCycleCountStatusDescriptor,
    InventoryFoundationMetricDescriptor,
    InventoryFoundationSnapshotDesktopDto,
    InventoryLocationCreateCommand,
    InventoryLocationTypeDescriptor,
    InventoryLocationUpdateCommand,
    InventoryModuleLinkDescriptor,
    InventoryReorderPolicyDesktopDto,
    InventoryReorderPolicyUpsertCommand,
    InventoryStorageLocationDesktopDto,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.serializers import (
    serialize_cycle_count,
    serialize_foundation_signal,
    serialize_reorder_policy,
    serialize_storage_location,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation import (
    CycleCountStatus,
    StorageLocationType,
)


class InventoryDesktopFoundationMixin:
    def list_location_types(self) -> tuple[InventoryLocationTypeDescriptor, ...]:
        return tuple(
            InventoryLocationTypeDescriptor(
                value=entry.value,
                label=format_enum_label(entry.value),
            )
            for entry in StorageLocationType
        )

    def list_cycle_count_statuses(self) -> tuple[InventoryCycleCountStatusDescriptor, ...]:
        return tuple(
            InventoryCycleCountStatusDescriptor(
                value=entry.value,
                label=format_enum_label(entry.value),
            )
            for entry in CycleCountStatus
        )

    def list_storage_locations(
        self,
        *,
        storeroom_id: str | None = None,
        site_id: str | None = None,
        active_only: bool | None = None,
    ) -> tuple[InventoryStorageLocationDesktopDto, ...]:
        service = self._require_foundation_service()
        allowed_storeroom_ids = self._allowed_storeroom_ids(site_id=site_id)
        storeroom_lookup = self._storeroom_lookup()
        rows = service.list_storage_locations(
            storeroom_id=storeroom_id,
            active_only=active_only,
        )
        filtered_rows = tuple(
            row
            for row in rows
            if allowed_storeroom_ids is None or row.storeroom_id in allowed_storeroom_ids
        )
        parent_lookup = {
            row.id: f"{row.location_code} - {row.name}"
            for row in filtered_rows
        }
        return tuple(
            serialize_storage_location(
                row,
                storeroom_lookup=storeroom_lookup,
                parent_lookup=parent_lookup,
            )
            for row in filtered_rows
        )

    def create_storage_location(
        self,
        command: InventoryLocationCreateCommand,
    ) -> InventoryStorageLocationDesktopDto:
        location = self._require_foundation_service().create_storage_location(
            storeroom_id=command.storeroom_id,
            location_code=command.location_code,
            name=command.name,
            parent_location_id=command.parent_location_id,
            location_type=command.location_type,
            is_active=command.is_active,
            is_quarantine=command.is_quarantine,
            allows_issue=command.allows_issue,
            allows_putaway=command.allows_putaway,
            notes=command.notes,
        )
        return self._serialize_storage_location(location)

    def update_storage_location(
        self,
        command: InventoryLocationUpdateCommand,
    ) -> InventoryStorageLocationDesktopDto:
        location = self._require_foundation_service().update_storage_location(
            command.location_id,
            location_code=command.location_code,
            name=command.name,
            parent_location_id=command.parent_location_id,
            location_type=command.location_type,
            is_active=command.is_active,
            is_quarantine=command.is_quarantine,
            allows_issue=command.allows_issue,
            allows_putaway=command.allows_putaway,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_storage_location(location)

    def list_reorder_policies(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        site_id: str | None = None,
        active_only: bool | None = None,
    ) -> tuple[InventoryReorderPolicyDesktopDto, ...]:
        service = self._require_foundation_service()
        allowed_storeroom_ids = self._allowed_storeroom_ids(site_id=site_id)
        rows = service.list_reorder_policies(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            active_only=active_only,
        )
        filtered_rows = tuple(
            row
            for row in rows
            if allowed_storeroom_ids is None or row.storeroom_id in allowed_storeroom_ids
        )
        return tuple(
            serialize_reorder_policy(
                row,
                item_lookup=self._item_lookup(),
                storeroom_lookup=self._storeroom_lookup(),
                location_lookup=self._location_lookup(site_id=site_id),
                party_lookup=self._party_lookup(),
            )
            for row in filtered_rows
        )

    def upsert_reorder_policy(
        self,
        command: InventoryReorderPolicyUpsertCommand,
    ) -> InventoryReorderPolicyDesktopDto:
        policy = self._require_foundation_service().upsert_reorder_policy(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            location_id=command.location_id,
            policy_name=command.policy_name,
            is_active=command.is_active,
            min_qty=command.min_qty,
            max_qty=command.max_qty,
            reorder_point=command.reorder_point,
            reorder_qty=command.reorder_qty,
            economic_order_qty=command.economic_order_qty,
            lead_time_days=command.lead_time_days,
            review_period_days=command.review_period_days,
            preferred_supplier_party_id=command.preferred_supplier_party_id,
            policy_id=command.policy_id,
            expected_version=command.expected_version,
        )
        return self._serialize_reorder_policy(policy)

    def list_cycle_counts(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        site_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryCycleCountDesktopDto, ...]:
        service = self._require_foundation_service()
        allowed_storeroom_ids = self._allowed_storeroom_ids(site_id=site_id)
        rows = service.list_cycle_counts(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            status=status,
            limit=limit,
        )
        filtered_rows = tuple(
            row
            for row in rows
            if allowed_storeroom_ids is None or row.storeroom_id in allowed_storeroom_ids
        )
        return tuple(
            serialize_cycle_count(
                row,
                item_lookup=self._item_lookup(),
                storeroom_lookup=self._storeroom_lookup(),
                location_lookup=self._location_lookup(site_id=site_id),
            )
            for row in filtered_rows
        )

    def schedule_cycle_count(
        self,
        command: InventoryCycleCountCreateCommand,
    ) -> InventoryCycleCountDesktopDto:
        cycle_count = self._require_foundation_service().schedule_cycle_count(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            location_id=command.location_id,
            scheduled_count_date=command.scheduled_count_date,
            notes=command.notes,
        )
        return self._serialize_cycle_count(cycle_count)

    def complete_cycle_count(
        self,
        command: InventoryCycleCountCompleteCommand,
    ) -> InventoryCycleCountDesktopDto:
        cycle_count = self._require_foundation_service().complete_cycle_count(
            command.cycle_count_id,
            counted_qty=command.counted_qty,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_cycle_count(cycle_count)

    def build_foundation_snapshot(
        self,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        stock_item_id: str | None = None,
        limit: int = 12,
    ) -> InventoryFoundationSnapshotDesktopDto:
        if self._foundation_service is None:
            return self.build_empty_foundation_snapshot()
        locations = self.list_storage_locations(
            storeroom_id=storeroom_id,
            site_id=site_id,
            active_only=None,
        )
        reorder_policies = self.list_reorder_policies(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            site_id=site_id,
            active_only=None,
        )
        cycle_counts = self.list_cycle_counts(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            site_id=site_id,
            limit=limit,
        )
        allowed_storeroom_ids = self._allowed_storeroom_ids(site_id=site_id)
        reservations = self._foundation_reservations(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            allowed_storeroom_ids=allowed_storeroom_ids,
        )
        requisitions = self._foundation_requisitions(
            storeroom_id=storeroom_id,
            site_id=site_id,
            limit=limit,
        )
        metrics = (
            InventoryFoundationMetricDescriptor(
                label="Locations",
                value=str(len(locations)),
                supporting_text="Zone, bin, shelf, and staging points beneath the selected storeroom scope.",
            ),
            InventoryFoundationMetricDescriptor(
                label="Reorder Policies",
                value=str(len(reorder_policies)),
                supporting_text="Active replenishment rules and preferred sourcing controls.",
            ),
            InventoryFoundationMetricDescriptor(
                label="Cycle Counts",
                value=str(len(cycle_counts)),
                supporting_text="Scheduled and completed count events within the selected scope.",
            ),
            InventoryFoundationMetricDescriptor(
                label="Reservations",
                value=str(len(reservations)),
                supporting_text="Demand/reservation records still affecting available stock.",
            ),
            InventoryFoundationMetricDescriptor(
                label="Open Procurement",
                value=str(len(requisitions)),
                supporting_text="Replenishment requests feeding the inventory supply chain.",
            ),
        )
        return InventoryFoundationSnapshotDesktopDto(
            title="Enterprise Inventory Backbone",
            subtitle="Warehouse locations, replenishment rules, cycle counts, valuation signals, and entitlement-aware cross-module readiness.",
            metrics=metrics,
            module_links=self._module_links(),
            locations=locations,
            reorder_policies=reorder_policies,
            cycle_counts=cycle_counts,
            valuation_signals=self._valuation_signals(
                site_id=site_id,
                storeroom_id=storeroom_id,
                limit=limit,
            ),
            tracking_signals=self._tracking_signals(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                allowed_storeroom_ids=allowed_storeroom_ids,
                limit=limit,
            ),
            activity_signals=self._activity_signals(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                allowed_storeroom_ids=allowed_storeroom_ids,
                limit=limit,
            ),
        )

    @staticmethod
    def build_empty_foundation_snapshot() -> InventoryFoundationSnapshotDesktopDto:
        return InventoryFoundationSnapshotDesktopDto(
            title="Enterprise Inventory Backbone",
            subtitle="Inventory foundation desktop API is not connected.",
            metrics=(),
            module_links=(),
            locations=(),
            reorder_policies=(),
            cycle_counts=(),
            valuation_signals=(),
            tracking_signals=(),
            activity_signals=(),
        )

    def _module_links(self) -> tuple[InventoryModuleLinkDescriptor, ...]:
        runtime = self._module_runtime_service
        if runtime is None:
            return (
                InventoryModuleLinkDescriptor(
                    code="project_management",
                    label="Project Management",
                    kind="module",
                    is_enabled=False,
                    status_label="Unavailable",
                    reason="Module runtime catalog is not connected.",
                    route_id="project_management.dashboard",
                ),
            )
        capability_codes = set(runtime.enabled_capability_codes())
        return (
            self._build_module_link(
                code="project_management",
                label="Project Management",
                route_id="project_management.dashboard",
            ),
            self._build_module_link(
                code="maintenance_management",
                label="Maintenance / CMMS",
                route_id="maintenance.dashboard",
            ),
            InventoryModuleLinkDescriptor(
                code="documents",
                label="Document Control",
                kind="capability",
                is_enabled="documents" in capability_codes,
                status_label="Enabled" if "documents" in capability_codes else "Unavailable",
                reason=""
                if "documents" in capability_codes
                else "Shared document capability is not available for the current platform context.",
                route_id="",
            ),
            InventoryModuleLinkDescriptor(
                code="approvals",
                label="Approval Workflows",
                kind="capability",
                is_enabled="approvals" in capability_codes,
                status_label="Enabled" if "approvals" in capability_codes else "Unavailable",
                reason=""
                if "approvals" in capability_codes
                else "Shared approval capability is not available for the current platform context.",
                route_id="",
            ),
        )

    def _build_module_link(
        self,
        *,
        code: str,
        label: str,
        route_id: str,
    ) -> InventoryModuleLinkDescriptor:
        runtime = self._module_runtime_service
        entitlement = runtime.get_entitlement(code) if runtime is not None else None
        is_enabled = bool(runtime and runtime.is_enabled(code))
        lifecycle_status = getattr(entitlement, "lifecycle_status", "")
        status_label = "Enabled" if is_enabled else format_enum_label(lifecycle_status or "unavailable")
        reason = ""
        if not is_enabled:
            reason = f"{label} is not enabled for the active organization."
        return InventoryModuleLinkDescriptor(
            code=code,
            label=label,
            kind="module",
            is_enabled=is_enabled,
            status_label=status_label,
            reason=reason,
            route_id=route_id,
        )

    def _valuation_signals(
        self,
        *,
        site_id: str | None,
        storeroom_id: str | None,
        limit: int,
    ):
        if self._reporting_service is None:
            return ()
        report = self._reporting_service.build_stock_status_report(
            site_id=site_id,
            storeroom_id=storeroom_id,
        )
        rows = sorted(
            report.rows,
            key=lambda row: float(row.on_hand_qty or 0.0) * float(row.average_cost or 0.0),
            reverse=True,
        )
        return tuple(
            serialize_foundation_signal(
                signal_id=f"valuation:{row.item_code}:{row.storeroom_code}",
                title=f"{row.item_code} - {row.item_name}",
                subtitle=f"{row.storeroom_code} - {row.storeroom_name}",
                status_label="Reorder" if row.reorder_required else "Valuation",
                supporting_text=f"On hand {row.on_hand_qty:.2f} {row.uom} | Available {row.available_qty:.2f}",
                meta_text=(
                    f"Inventory value {format_amount(float(row.on_hand_qty or 0.0) * float(row.average_cost or 0.0))} | "
                    f"Avg cost {format_amount(row.average_cost)}"
                ),
                tone="warning" if row.reorder_required else "default",
            )
            for row in rows[: max(1, int(limit or 12))]
        )

    def _tracking_signals(
        self,
        *,
        stock_item_id: str | None,
        storeroom_id: str | None,
        allowed_storeroom_ids: set[str] | None,
        limit: int,
    ):
        if self._purchasing_service is None:
            return ()
        item_lookup = self._item_lookup()
        storeroom_lookup = self._storeroom_lookup()
        signals = []
        receipts = self._purchasing_service.list_receipts(limit=max(25, int(limit or 12)))
        for receipt in receipts:
            for line in self._purchasing_service.list_receipt_lines(receipt.id):
                if stock_item_id and line.stock_item_id != stock_item_id:
                    continue
                if storeroom_id and line.storeroom_id != storeroom_id:
                    continue
                if allowed_storeroom_ids is not None and line.storeroom_id not in allowed_storeroom_ids:
                    continue
                has_tracking = bool(
                    getattr(line, "lot_number", "")
                    or getattr(line, "serial_number", "")
                    or getattr(line, "expiry_date", None)
                )
                if not has_tracking:
                    continue
                expiry_date = getattr(line, "expiry_date", None)
                status_label = "Tracked"
                tone = "default"
                if isinstance(expiry_date, date):
                    if expiry_date < date.today():
                        status_label = "Expired"
                        tone = "danger"
                    elif expiry_date <= date.today() + timedelta(days=30):
                        status_label = "Expiring"
                        tone = "warning"
                signals.append(
                    serialize_foundation_signal(
                        signal_id=f"tracking:{line.id}",
                        title=item_lookup.get(line.stock_item_id, line.stock_item_id),
                        subtitle=storeroom_lookup.get(line.storeroom_id, line.storeroom_id),
                        status_label=status_label,
                        supporting_text=" | ".join(
                            bit
                            for bit in (
                                f"Lot {line.lot_number}" if getattr(line, "lot_number", "") else "",
                                f"Serial {line.serial_number}" if getattr(line, "serial_number", "") else "",
                                f"Accepted {float(line.quantity_accepted or 0.0):.2f} {line.uom}",
                            )
                            if bit
                        ),
                        meta_text=" | ".join(
                            bit
                            for bit in (
                                f"Receipt {receipt.receipt_number}",
                                f"Expiry {format_date(expiry_date)}" if expiry_date else "",
                            )
                            if bit
                        ),
                        tone=tone,
                    )
                )
        return tuple(signals[: max(1, int(limit or 12))])

    def _activity_signals(
        self,
        *,
        stock_item_id: str | None,
        storeroom_id: str | None,
        allowed_storeroom_ids: set[str] | None,
        limit: int,
    ):
        if self._stock_service is None:
            return ()
        item_lookup = self._item_lookup()
        storeroom_lookup = self._storeroom_lookup()
        transactions = self._stock_service.list_transactions(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            limit=max(1, int(limit or 12)),
        )
        filtered = [
            row
            for row in transactions
            if allowed_storeroom_ids is None or row.storeroom_id in allowed_storeroom_ids
        ]
        return tuple(
            serialize_foundation_signal(
                signal_id=row.id,
                title=row.transaction_number,
                subtitle=f"{item_lookup.get(row.stock_item_id, row.stock_item_id)} @ {storeroom_lookup.get(row.storeroom_id, row.storeroom_id)}",
                status_label=format_enum_label(getattr(getattr(row, "transaction_type", None), "value", getattr(row, "transaction_type", ""))),
                supporting_text=(
                    f"{float(row.quantity or 0.0):.2f} {row.uom} | "
                    f"On hand {float(row.resulting_on_hand_qty or 0.0):.2f}"
                ),
                meta_text=" | ".join(
                    bit
                    for bit in (
                        format_date(getattr(row, "transaction_at", None)),
                        getattr(row, "performed_by_username", "") or "",
                        f"Ref {row.reference_type}/{row.reference_id}"
                        if (getattr(row, "reference_type", "") or getattr(row, "reference_id", ""))
                        else "",
                    )
                    if bit
                ),
            )
            for row in filtered[: max(1, int(limit or 12))]
        )

    def _foundation_reservations(
        self,
        *,
        stock_item_id: str | None,
        storeroom_id: str | None,
        allowed_storeroom_ids: set[str] | None,
    ):
        if self._reservation_service is None:
            return ()
        rows = self._reservation_service.list_reservations(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            limit=200,
        )
        return tuple(
            row
            for row in rows
            if allowed_storeroom_ids is None or row.storeroom_id in allowed_storeroom_ids
        )

    def _foundation_requisitions(
        self,
        *,
        storeroom_id: str | None,
        site_id: str | None,
        limit: int,
    ):
        if self._procurement_service is None:
            return ()
        return tuple(
            self._procurement_service.list_requisitions(
                site_id=site_id,
                storeroom_id=storeroom_id,
                limit=max(1, int(limit or 12)),
            )
        )

    def _serialize_storage_location(self, row) -> InventoryStorageLocationDesktopDto:
        location_lookup = {
            location.id: f"{location.location_code} - {location.name}"
            for location in self._foundation_service.list_storage_locations(active_only=None)
        }
        return serialize_storage_location(
            row,
            storeroom_lookup=self._storeroom_lookup(),
            parent_lookup=location_lookup,
        )

    def _serialize_reorder_policy(self, row) -> InventoryReorderPolicyDesktopDto:
        return serialize_reorder_policy(
            row,
            item_lookup=self._item_lookup(),
            storeroom_lookup=self._storeroom_lookup(),
            location_lookup=self._location_lookup(site_id=None),
            party_lookup=self._party_lookup(),
        )

    def _serialize_cycle_count(self, row) -> InventoryCycleCountDesktopDto:
        return serialize_cycle_count(
            row,
            item_lookup=self._item_lookup(),
            storeroom_lookup=self._storeroom_lookup(),
            location_lookup=self._location_lookup(site_id=None),
        )

    def _allowed_storeroom_ids(self, *, site_id: str | None) -> set[str] | None:
        if not site_id or self._inventory_service is None:
            return None
        return {
            row.id
            for row in self._inventory_service.list_storerooms(
                active_only=None,
                site_id=site_id,
            )
        }

    def _item_lookup(self) -> dict[str, str]:
        if self._item_service is None:
            return {}
        return {
            row.id: " - ".join(part for part in (row.item_code, row.name) if part)
            for row in self._item_service.list_items(active_only=None)
        }

    def _storeroom_lookup(self) -> dict[str, str]:
        if self._inventory_service is None:
            return {}
        return {
            row.id: " - ".join(part for part in (row.storeroom_code, row.name) if part)
            for row in self._inventory_service.list_storerooms(active_only=None)
        }

    def _location_lookup(self, *, site_id: str | None) -> dict[str, str]:
        if self._foundation_service is None:
            return {}
        allowed_storeroom_ids = self._allowed_storeroom_ids(site_id=site_id)
        rows = self._foundation_service.list_storage_locations(active_only=None)
        return {
            row.id: " - ".join(part for part in (row.location_code, row.name) if part)
            for row in rows
            if allowed_storeroom_ids is None or row.storeroom_id in allowed_storeroom_ids
        }

    def _require_foundation_service(self):
        if self._foundation_service is None:
            raise RuntimeError("Inventory foundation desktop API is not connected.")
        return self._foundation_service


__all__ = ["InventoryDesktopFoundationMixin"]
