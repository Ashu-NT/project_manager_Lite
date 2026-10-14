"""Auth command handlers."""

from src.core.platform.application.security.auth.commands.authentication import (
    AuthenticationHandler,
)
from src.core.platform.application.security.auth.commands.bootstrap import (
    AuthBootstrapHandler,
)
from src.core.platform.application.security.auth.commands.context_switch import (
    ContextSwitchCommandHandler,
)
from src.core.platform.application.security.auth.commands.federated_identity import (
    FederatedIdentityCommandHandler,
)
from src.core.platform.application.security.auth.commands.mfa import MfaCommandHandler
from src.core.platform.application.security.auth.commands.password import (
    PasswordCommandHandler,
)
from src.core.platform.application.security.auth.commands.platform_owner import (
    PlatformOwnerProvisioningHandler,
)
from src.core.platform.application.security.auth.commands.registration import (
    UserRegistrationHandler,
)
from src.core.platform.application.security.auth.commands.sessions import (
    AuthSessionCommandHandler,
)
from src.core.platform.application.security.auth.commands.user_administration import (
    UserAdministrationCommandHandler,
)

__all__ = [
    "AuthBootstrapHandler",
    "AuthSessionCommandHandler",
    "AuthenticationHandler",
    "ContextSwitchCommandHandler",
    "FederatedIdentityCommandHandler",
    "MfaCommandHandler",
    "PasswordCommandHandler",
    "PlatformOwnerProvisioningHandler",
    "UserAdministrationCommandHandler",
    "UserRegistrationHandler",
]
