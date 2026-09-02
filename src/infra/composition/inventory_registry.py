from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session, sessionmaker

from src.infra.time.system_clock import SystemClock
from src.core.platform.access import ScopedRolePolicy
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.modules.inventory_procurement import (
    InventoryDataExchangeService,
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.access.policy import (
    STOREROOM_SCOPE_ROLE_CHOICES,
    normalize_storeroom_scope_role,
    resolve_storeroom_scope_permissions,
)
from src.core.modules.inventory_procurement.application.catalog import (
    ItemCategoryService,
    ItemMasterService,
)
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryFoundationService,
    InventoryService,
    ReservationService,
    StockControlService,
)
from src.core.modules.inventory_procurement.application.procurement import (
    ProcurementService,
    PurchasingService,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.purchase_order_submission_unit_of_work import (
    SqlAlchemyPurchaseOrderSubmissionUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.requisition_submission_unit_of_work import (
    SqlAlchemyRequisitionSubmissionUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.reservation_unit_of_work import (
    SqlAlchemyInventoryReservationUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.uow.inventory.inventory_foundation_unit_of_work import (
    SqlAlchemyInventoryFoundationUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.uow.catalog.inventory_catalog_unit_of_work import (
    SqlAlchemyInventoryCatalogUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    build_balance_view_invalidation_handler,
    build_cycle_count_view_invalidation_handler,
    build_location_list_view_invalidation_handler,
    build_reorder_policy_list_view_invalidation_handler,
    build_reservation_view_invalidation_handler,
    build_storeroom_list_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.application.catalog.event_handlers.view_invalidation import (
    build_item_category_list_view_invalidation_handler,
    build_item_list_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.application.procurement.event_handlers.view_invalidation import (
    build_purchase_order_view_invalidation_handler,
    build_receipt_view_invalidation_handler,
    build_requisition_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation_events import (
    InventoryReorderPolicyConfigured,
    LocationCreated,
    LocationProfileUpdated,
    StoreroomCreated,
    StoreroomProfileUpdated,
    StoreroomStatusChanged,
)
from src.core.modules.inventory_procurement.domain.catalog.catalog_events import (
    InventoryItemCategoryCreated,
    InventoryItemCategoryProfileUpdated,
    InventoryItemCreated,
    InventoryItemProfileUpdated,
    InventoryItemStatusChanged,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing_events import (
    InventoryPurchaseOrderApproved,
    InventoryPurchaseOrderCancelled,
    InventoryPurchaseOrderClosed,
    InventoryPurchaseOrderCreated,
    InventoryPurchaseOrderLineAdded,
    InventoryPurchaseOrderProfileUpdated,
    InventoryPurchaseOrderReceivingAdvanced,
    InventoryPurchaseOrderRejected,
    InventoryPurchaseOrderSent,
    InventoryPurchaseOrderSubmitted,
)
from src.core.modules.inventory_procurement.domain.procurement.receipt_events import (
    InventoryReceiptPosted,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionApproved,
    InventoryRequisitionCancelled,
    InventoryRequisitionCreated,
    InventoryRequisitionLineAdded,
    InventoryRequisitionProfileUpdated,
    InventoryRequisitionRejected,
    InventoryRequisitionSourcingAdvanced,
    InventoryRequisitionSubmitted,
)
from src.core.modules.inventory_procurement.domain.inventory.reservation_events import (
    InventoryReservationCancelled,
    InventoryReservationConsumptionAdvanced,
    InventoryReservationCreated,
    InventoryReservationReleased,
)
from src.core.modules.inventory_procurement.domain.inventory.balance_events import (
    StockOnHandQuantityChanged,
    StockOnOrderQuantityChanged,
    StockReservedQuantityChanged,
)
from src.core.modules.inventory_procurement.domain.inventory.cycle_count_events import (
    InventoryCycleCountCompleted,
    InventoryCycleCountScheduled,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.catalog import (
    SqlAlchemyInventoryItemCategoryRepository,
    SqlAlchemyStockItemRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyCycleCountRepository,
    SqlAlchemyReorderPolicyRepository,
    SqlAlchemyStockBalanceRepository,
    SqlAlchemyStockReservationRepository,
    SqlAlchemyStockTransactionRepository,
    SqlAlchemyStorageLocationRepository,
    SqlAlchemyStoreroomRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseOrderLineRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
    SqlAlchemyReceiptLineRepository,
)
from src.core.modules.inventory_procurement.infrastructure.reporting import InventoryReportingService
from src.core.modules.inventory_procurement.infrastructure.approval.procurement_apply_participant import (
    ProcurementApprovalParticipant,
)
from src.core.modules.inventory_procurement.infrastructure.approval.purchasing_apply_participant import (
    PurchasingApprovalParticipant,
)
from src.infra.composition.approval_apply_dependencies.procurement import (
    build_procurement_approval_deps,
)
from src.infra.composition.approval_apply_dependencies.purchasing import (
    build_purchasing_approval_deps,
)
from src.infra.composition.platform_registry import PlatformServiceBundle
from src.core.platform.application.integration import IntegrationOutboxService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InventoryProcurementServiceBundle:
    inventory_reference_service: InventoryReferenceService
    inventory_data_exchange_service: InventoryDataExchangeService
    inventory_reporting_service: InventoryReportingService
    inventory_item_category_service: ItemCategoryService
    inventory_item_service: ItemMasterService
    inventory_foundation_service: InventoryFoundationService
    inventory_service: InventoryService
    inventory_stock_service: StockControlService
    inventory_reservation_service: ReservationService
    inventory_procurement_service: ProcurementService
    inventory_purchasing_service: PurchasingService


def build_inventory_procurement_service_bundle(
    platform_services: PlatformServiceBundle,
    *,
    procurement_financial_outbox_service: IntegrationOutboxService | None = None,
) -> InventoryProcurementServiceBundle:
    started = perf_counter()
    logger.debug("Inventory/Procurement service bundle build begin")
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="storeroom",
            role_choices=STOREROOM_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_storeroom_scope_role,
            resolve_permissions=resolve_storeroom_scope_permissions,
        )
    )
    logger.debug("Inventory/Procurement storeroom access policy registered")
    logger.debug("Inventory/Procurement repositories build begin")
    balance_repo = SqlAlchemyStockBalanceRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    category_repo = SqlAlchemyInventoryItemCategoryRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    item_repo = SqlAlchemyStockItemRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    purchase_order_line_repo = SqlAlchemyPurchaseOrderLineRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    purchase_order_repo = SqlAlchemyPurchaseOrderRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    requisition_line_repo = SqlAlchemyPurchaseRequisitionLineRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    requisition_repo = SqlAlchemyPurchaseRequisitionRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    receipt_header_repo = SqlAlchemyReceiptHeaderRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    receipt_line_repo = SqlAlchemyReceiptLineRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    cycle_count_repo = SqlAlchemyCycleCountRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    location_repo = SqlAlchemyStorageLocationRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    reorder_policy_repo = SqlAlchemyReorderPolicyRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    reservation_repo = SqlAlchemyStockReservationRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    transaction_repo = SqlAlchemyStockTransactionRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    storeroom_repo = SqlAlchemyStoreroomRepository(
        platform_services.session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    logger.debug("Inventory/Procurement repositories built")
    logger.debug("Inventory/Procurement core services build begin")
    inventory_catalog_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    inventory_catalog_uow_factory = SqlAlchemyInventoryCatalogUnitOfWorkFactory(
        session_factory=inventory_catalog_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    _item_list_view_invalidation_handler = build_item_list_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _item_event_type in (
        InventoryItemCreated,
        InventoryItemProfileUpdated,
        InventoryItemStatusChanged,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _item_event_type, _item_list_view_invalidation_handler
        )
    _item_category_list_view_invalidation_handler = build_item_category_list_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _item_category_event_type in (
        InventoryItemCategoryCreated,
        InventoryItemCategoryProfileUpdated,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _item_category_event_type, _item_category_list_view_invalidation_handler
        )
    inventory_item_category_service = ItemCategoryService(
        platform_services.session,
        category_repo,
        organization_repo=platform_services.organization_repo,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        uow_factory=inventory_catalog_uow_factory,
    )

    inventory_foundation_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    inventory_foundation_uow_factory = SqlAlchemyInventoryFoundationUnitOfWorkFactory(
        session_factory=inventory_foundation_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        organization_repo=platform_services.organization_repo,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    _storeroom_list_view_invalidation_handler = build_storeroom_list_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _storeroom_event_type in (StoreroomCreated, StoreroomProfileUpdated, StoreroomStatusChanged):
        platform_services.platform_post_commit_bus.subscribe(
            _storeroom_event_type, _storeroom_list_view_invalidation_handler
        )
    _location_list_view_invalidation_handler = build_location_list_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _location_event_type in (LocationCreated, LocationProfileUpdated):
        platform_services.platform_post_commit_bus.subscribe(
            _location_event_type, _location_list_view_invalidation_handler
        )
    _reorder_policy_list_view_invalidation_handler = build_reorder_policy_list_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    platform_services.platform_post_commit_bus.subscribe(
        InventoryReorderPolicyConfigured, _reorder_policy_list_view_invalidation_handler
    )
    inventory_service = InventoryService(
        platform_services.session,
        storeroom_repo,
        organization_repo=platform_services.organization_repo,
        site_service=platform_services.site_service,
        party_service=platform_services.party_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        uow_factory=inventory_foundation_uow_factory,
    )
    inventory_item_service = ItemMasterService(
        platform_services.session,
        item_repo,
        category_repo=category_repo,
        organization_repo=platform_services.organization_repo,
        party_service=platform_services.party_service,
        document_integration_service=platform_services.document_integration_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        uow_factory=inventory_catalog_uow_factory,
    )

    inventory_foundation_uow_factory.configure_stock_dependencies(
        item_service=inventory_item_service,
        inventory_service=inventory_service,
    )

    requisition_submission_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    requisition_submission_uow_factory = SqlAlchemyRequisitionSubmissionUnitOfWorkFactory(
        session_factory=requisition_submission_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    inventory_procurement_service = ProcurementService(
        platform_services.session,
        requisition_repo,
        requisition_line_repo,
        organization_repo=platform_services.organization_repo,
        inventory_service=inventory_service,
        item_service=inventory_item_service,
        party_service=platform_services.party_service,
        approval_service=platform_services.approval_service,
        requisition_submission_uow_factory=requisition_submission_uow_factory,
        clock=SystemClock(),
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    inventory_stock_service = StockControlService(
        platform_services.session,
        balance_repo,
        transaction_repo,
        organization_repo=platform_services.organization_repo,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    purchase_order_submission_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    purchase_order_submission_uow_factory = SqlAlchemyPurchaseOrderSubmissionUnitOfWorkFactory(
        session_factory=purchase_order_submission_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    def _build_purchase_order_receiving_collaborators(session: Session):
        receipt_header_repo = SqlAlchemyReceiptHeaderRepository(
            session, tenant_context_service=platform_services.tenant_context_service
        )
        receipt_line_repo = SqlAlchemyReceiptLineRepository(
            session, tenant_context_service=platform_services.tenant_context_service
        )
        stock_service = StockControlService(
            session,
            SqlAlchemyStockBalanceRepository(
                session, tenant_context_service=platform_services.tenant_context_service
            ),
            SqlAlchemyStockTransactionRepository(
                session, tenant_context_service=platform_services.tenant_context_service
            ),
            organization_repo=platform_services.organization_repo,
            item_service=inventory_item_service,
            inventory_service=inventory_service,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
        )
        return receipt_header_repo, receipt_line_repo, stock_service

    inventory_purchasing_service = PurchasingService(
        platform_services.session,
        purchase_order_repo,
        purchase_order_line_repo,
        receipt_header_repo,
        receipt_line_repo,
        requisition_repo=requisition_repo,
        requisition_line_repo=requisition_line_repo,
        balance_repo=balance_repo,
        organization_repo=platform_services.organization_repo,
        reference_service=InventoryReferenceService(
            site_service=platform_services.site_service,
            party_service=platform_services.party_service,
            user_session=platform_services.user_session,
        ),
        inventory_service=inventory_service,
        item_service=inventory_item_service,
        stock_service=inventory_stock_service,
        approval_service=platform_services.approval_service,
        purchase_order_submission_uow_factory=purchase_order_submission_uow_factory,
        clock=SystemClock(),
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        document_integration_service=platform_services.document_integration_service,
        procurement_financial_outbox_service=procurement_financial_outbox_service,
        receiving_collaborators_factory=_build_purchase_order_receiving_collaborators,
    )
    _purchase_order_view_invalidation_handler = build_purchase_order_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _purchase_order_event_type in (
        InventoryPurchaseOrderCreated,
        InventoryPurchaseOrderLineAdded,
        InventoryPurchaseOrderProfileUpdated,
        InventoryPurchaseOrderSubmitted,
        InventoryPurchaseOrderApproved,
        InventoryPurchaseOrderRejected,
        InventoryPurchaseOrderCancelled,
        InventoryPurchaseOrderSent,
        InventoryPurchaseOrderClosed,
        InventoryPurchaseOrderReceivingAdvanced,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _purchase_order_event_type, _purchase_order_view_invalidation_handler
        )
    _requisition_view_invalidation_handler = build_requisition_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _requisition_event_type in (
        InventoryRequisitionCreated,
        InventoryRequisitionLineAdded,
        InventoryRequisitionProfileUpdated,
        InventoryRequisitionSubmitted,
        InventoryRequisitionApproved,
        InventoryRequisitionRejected,
        InventoryRequisitionCancelled,
        InventoryRequisitionSourcingAdvanced,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _requisition_event_type, _requisition_view_invalidation_handler
        )
    _receipt_view_invalidation_handler = build_receipt_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    platform_services.platform_post_commit_bus.subscribe(
        InventoryReceiptPosted, _receipt_view_invalidation_handler
    )

    inventory_reservation_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    inventory_reservation_uow_factory = SqlAlchemyInventoryReservationUnitOfWorkFactory(
        session_factory=inventory_reservation_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        organization_repo=platform_services.organization_repo,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    _reservation_view_invalidation_handler = build_reservation_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _reservation_event_type in (
        InventoryReservationCreated,
        InventoryReservationConsumptionAdvanced,
        InventoryReservationReleased,
        InventoryReservationCancelled,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _reservation_event_type, _reservation_view_invalidation_handler
        )
    _balance_view_invalidation_handler = build_balance_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _balance_event_type in (
        StockOnHandQuantityChanged,
        StockReservedQuantityChanged,
        StockOnOrderQuantityChanged,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _balance_event_type, _balance_view_invalidation_handler
        )
    _cycle_count_view_invalidation_handler = build_cycle_count_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _cycle_count_event_type in (
        InventoryCycleCountScheduled,
        InventoryCycleCountCompleted,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _cycle_count_event_type, _cycle_count_view_invalidation_handler
        )
    inventory_reservation_service = ReservationService(
        platform_services.session,
        reservation_repo,
        organization_repo=platform_services.organization_repo,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        reservation_uow_factory=inventory_reservation_uow_factory,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        document_integration_service=platform_services.document_integration_service,
    )
    inventory_foundation_service = InventoryFoundationService(
        platform_services.session,
        location_repo,
        reorder_policy_repo,
        cycle_count_repo,
        organization_repo=platform_services.organization_repo,
        inventory_service=inventory_service,
        item_service=inventory_item_service,
        stock_service=inventory_stock_service,
        party_service=platform_services.party_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        uow_factory=inventory_foundation_uow_factory,
    )
    procurement_approval_participant = ProcurementApprovalParticipant()
    procurement_dependencies_factory = lambda uow_session: build_procurement_approval_deps(
        uow_session,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    platform_services.approval_service.register_apply_handler(
        "purchase_requisition.submit",
        procurement_approval_participant.apply,
        dependencies_factory=procurement_dependencies_factory,
    )
    platform_services.approval_service.register_reject_handler(
        "purchase_requisition.submit",
        procurement_approval_participant.reject,
        dependencies_factory=procurement_dependencies_factory,
    )
    purchasing_approval_participant = PurchasingApprovalParticipant()
    purchasing_dependencies_factory = lambda uow_session: build_purchasing_approval_deps(
        uow_session,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    platform_services.approval_service.register_apply_handler(
        "purchase_order.submit",
        purchasing_approval_participant.apply,
        dependencies_factory=purchasing_dependencies_factory,
    )
    platform_services.approval_service.register_reject_handler(
        "purchase_order.submit",
        purchasing_approval_participant.reject,
        dependencies_factory=purchasing_dependencies_factory,
    )
    inventory_reference_service = InventoryReferenceService(
        site_service=platform_services.site_service,
        party_service=platform_services.party_service,
        user_session=platform_services.user_session,
    )
    inventory_data_exchange_service = InventoryDataExchangeService(
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        procurement_service=inventory_procurement_service,
        purchasing_service=inventory_purchasing_service,
        approval_service=platform_services.approval_service,
        site_service=platform_services.site_service,
        party_service=platform_services.party_service,
        requisition_line_repo=requisition_line_repo,
        purchase_order_line_repo=purchase_order_line_repo,
        receipt_line_repo=receipt_line_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        runtime_execution_service=platform_services.runtime_execution_service,
    )
    inventory_reporting_service = InventoryReportingService(
        reference_service=inventory_reference_service,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        stock_service=inventory_stock_service,
        procurement_service=inventory_procurement_service,
        purchasing_service=inventory_purchasing_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        runtime_execution_service=platform_services.runtime_execution_service,
    )
    logger.debug("Inventory/Procurement core services built")

    def _storeroom_exists(tenant_id: str, storeroom_id: str) -> bool:
        storeroom = storeroom_repo.get_for_tenant(storeroom_id, tenant_id)
        return bool(
            storeroom is not None
            and storeroom.organization_id
            and platform_services.organization_repo.get_for_tenant(
                storeroom.organization_id, tenant_id
            )
            is not None
        )

    platform_services.access_service.register_scope_exists_resolver("storeroom", _storeroom_exists)
    platform_services.auth_service.register_canonical_scope_tenant_resolver(
        "storeroom", _storeroom_exists
    )

    def _storeroom_exists_for_role_governance(
        session: Session, tenant_id: str, storeroom_id: str
    ) -> bool:
        storeroom = SqlAlchemyStoreroomRepository(
            session, tenant_context_service=platform_services.tenant_context_service
        ).get_for_tenant(storeroom_id, tenant_id)
        if storeroom is None or not storeroom.organization_id:
            return False
        return (
            SqlAlchemyOrganizationRepository(session).get_for_tenant(
                storeroom.organization_id, tenant_id
            )
            is not None
        )

    def _storeroom_organization_owner_for_role_governance(
        session: Session, tenant_id: str, storeroom_id: str
    ) -> str | None:
        storeroom = SqlAlchemyStoreroomRepository(
            session, tenant_context_service=platform_services.tenant_context_service
        ).get_for_tenant(storeroom_id, tenant_id)
        return getattr(storeroom, "organization_id", None)

    platform_services.role_governance_service.register_scope_exists_resolver(
        "storeroom", _storeroom_exists_for_role_governance
    )
    platform_services.role_governance_service.register_organization_owner_resolver(
        "storeroom", _storeroom_organization_owner_for_role_governance
    )

    logger.debug(
        "Inventory/Procurement service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return InventoryProcurementServiceBundle(
        inventory_reference_service=inventory_reference_service,
        inventory_data_exchange_service=inventory_data_exchange_service,
        inventory_reporting_service=inventory_reporting_service,
        inventory_item_category_service=inventory_item_category_service,
        inventory_item_service=inventory_item_service,
        inventory_foundation_service=inventory_foundation_service,
        inventory_service=inventory_service,
        inventory_stock_service=inventory_stock_service,
        inventory_reservation_service=inventory_reservation_service,
        inventory_procurement_service=inventory_procurement_service,
        inventory_purchasing_service=inventory_purchasing_service,
    )


__all__ = ["InventoryProcurementServiceBundle", "build_inventory_procurement_service_bundle"]
