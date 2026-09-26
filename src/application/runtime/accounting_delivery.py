"""Sequential external Accounting runtime. Composition supplies the scoped processor."""

import argparse
import logging
import os
import signal
from threading import Event

from src.core.platform.application.integration.accounting.delivery_processor import (
    ExternalAccountingDeliveryProcessor,
)

logger = logging.getLogger(__name__)


def run_accounting_delivery(
    processor: ExternalAccountingDeliveryProcessor,
    *,
    stop: Event,
    idle_seconds: float = 5.0,
) -> None:
    if idle_seconds < 0.1 or idle_seconds > 300:
        raise ValueError("Accounting idle polling must be between 0.1 and 300 seconds.")
    while not stop.is_set():
        try:
            did_work = processor.process_one()
        except Exception:
            # No exception body: database/provider errors may contain private input.
            logger.error(
                "Accounting delivery operation failed; durable lease recovery will apply."
            )
            did_work = False
        if not did_work:
            stop.wait(idle_seconds)
    # An in-flight sequential attempt finalizes before this loop observes stop.


def main(argv=None, *, adapters=None, credentials=None) -> int:
    """Executable host; provider registration is trusted composition, not tenant data.

    No vendor provider ships with PM. Deployments register their authorized port
    and credential provider explicitly; an unconfigured host fails before DB work.
    """
    parser = argparse.ArgumentParser(description="External Accounting delivery worker")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--idle-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)
    if not adapters or credentials is None:
        logger.error(
            "No external Accounting transport/credential providers are installed."
        )
        return 2
    if not 0.1 <= args.idle_seconds <= 300:
        parser.error("--idle-seconds must be between 0.1 and 300")
    from sqlalchemy import create_engine

    from src.core.modules.project_management.infrastructure.persistence.uow.integration.accounting.accounting_delivery import (
        AccountingWorkerScope,
    )
    from src.infra.composition.integration.accounting.accounting_delivery import (
        build_external_accounting_processor,
    )
    from src.infra.platform.env_loader import load_env_file

    load_env_file()
    database_url = os.environ.get("PM_DB_URL", "").strip()
    if not database_url:
        logger.error("PM_DB_URL must select the migrated runtime database.")
        return 2
    # No schema bootstrap and no URL/raw SQL parameter logging in this worker.
    engine = create_engine(database_url, hide_parameters=True)
    stop = Event()
    previous = {}
    try:
        processor = build_external_accounting_processor(
            engine=engine,
            scope=AccountingWorkerScope(args.tenant, args.organization, args.project),
            principal_name=args.principal,
            adapters=adapters,
            credentials=credentials,
        )
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, lambda _signum, _frame: stop.set())
        run_accounting_delivery(processor, stop=stop, idle_seconds=args.idle_seconds)
        return 0
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
