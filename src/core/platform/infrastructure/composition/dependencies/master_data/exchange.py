"""Build entity-owned master-data exchange handlers and their runtimes."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.application.data_operations.exporting import (
    ExportDefinitionRegistry,
    ExportRuntime,
)
from src.core.platform.application.data_operations.importing import (
    CsvImportRuntime,
    ImportDefinitionRegistry,
)
from src.core.platform.application.master_data.data_exchange.commands.party_export import (
    PartyExportHandler,
)
from src.core.platform.application.master_data.data_exchange.commands.party_import import (
    PartyImportHandler,
)
from src.core.platform.application.master_data.data_exchange.commands.site_export import (
    SiteExportHandler,
)
from src.core.platform.application.master_data.data_exchange.commands.site_import import (
    SiteImportHandler,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


@dataclass(frozen=True)
class MasterDataExchangeComposition:
    import_runtime: CsvImportRuntime
    export_runtime: ExportRuntime


def build_master_data_exchange(
    *,
    site_commands: SiteCommandHandler,
    site_query: SiteQueryHandler,
    party_commands: PartyCommandHandler,
    party_query: PartyQueryHandler,
    user_session: UserSessionContext,
) -> MasterDataExchangeComposition:
    imports = ImportDefinitionRegistry()
    imports.register(SiteImportHandler(commands=site_commands, query=site_query))
    imports.register(PartyImportHandler(commands=party_commands, query=party_query))
    exports = ExportDefinitionRegistry()
    exports.register(SiteExportHandler(query=site_query))
    exports.register(PartyExportHandler(query=party_query))
    return MasterDataExchangeComposition(
        import_runtime=CsvImportRuntime(imports, user_session=user_session),
        export_runtime=ExportRuntime(exports, user_session=user_session),
    )
