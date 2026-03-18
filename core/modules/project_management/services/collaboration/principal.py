from __future__ import annotations

from core.platform.common.models import TaskComment


class CollaborationPrincipalMixin:
    def _comment_mentions_principal(self, comment: TaskComment) -> bool:
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        mentioned_user_ids = {str(item).strip() for item in comment.mentioned_user_ids if str(item).strip()}
        if principal_user_id and principal_user_id in mentioned_user_ids:
            return True
        mentions = {item.lower() for item in comment.mentions}
        aliases = self._principal_aliases()
        return bool(aliases and not mentions.isdisjoint(aliases))

    def _comment_is_unread_for_principal(self, comment: TaskComment) -> bool:
        if not self._comment_mentions_principal(comment):
            return False
        principal = self._user_session.principal if self._user_session is not None else None
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        if principal_user_id:
            read_by_user_ids = {str(item).strip() for item in comment.read_by_user_ids if str(item).strip()}
            if principal_user_id in read_by_user_ids:
                return False
        aliases = self._principal_aliases()
        read_by = {item.lower() for item in comment.read_by}
        return read_by.isdisjoint(aliases)

    def _principal_aliases(self) -> set[str]:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            return set()
        aliases: set[str] = set()
        if principal.username:
            aliases.add(principal.username.strip().lower())
        display_name = (principal.display_name or "").strip().lower()
        if display_name:
            aliases.add(display_name.strip(" @"))
            aliases.add(display_name.replace(" ", "").strip(" @"))
            aliases.add(display_name.replace(" ", ".").strip(" @"))
        return {alias for alias in aliases if alias}

    def _principal_primary_alias(self) -> str:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None or not getattr(principal, "username", None):
            return ""
        return str(principal.username).strip().lower()


__all__ = ["CollaborationPrincipalMixin"]
