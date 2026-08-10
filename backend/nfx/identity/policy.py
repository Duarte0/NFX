from __future__ import annotations

from enum import StrEnum

from nfx.identity.models import Role


class Action(StrEnum):
    CHANGE_OWN_PASSWORD = "change_own_password"
    ADMINISTER_USERS = "administer_users"
    ADMINISTER_COMPANIES = "administer_companies"
    ADMINISTER_CERTIFICATES = "administer_certificates"
    CONTROL_COLLECTIONS = "control_collections"
    READ_DOCUMENTS = "read_documents"
    DOWNLOAD_DOCUMENTS = "download_documents"
    CREATE_ZIP = "create_zip"
    DOWNLOAD_OWN_ZIP = "download_own_zip"
    DOWNLOAD_ANY_ZIP = "download_any_zip"
    READ_RETENTION = "read_retention"
    ADMINISTER_SYSTEM = "administer_system"


_OPERATOR_ACTIONS = frozenset(
    {
        Action.CHANGE_OWN_PASSWORD,
        Action.ADMINISTER_COMPANIES,
        Action.ADMINISTER_CERTIFICATES,
        Action.CONTROL_COLLECTIONS,
        Action.READ_DOCUMENTS,
        Action.DOWNLOAD_DOCUMENTS,
        Action.CREATE_ZIP,
        Action.DOWNLOAD_OWN_ZIP,
    }
)
_VIEWER_ACTIONS = frozenset(
    {
        Action.CHANGE_OWN_PASSWORD,
        Action.READ_DOCUMENTS,
        Action.DOWNLOAD_DOCUMENTS,
        Action.CREATE_ZIP,
        Action.DOWNLOAD_OWN_ZIP,
    }
)


def authorize(
    role: str, action: Action, *, owner_id: str | None = None, actor_id: str | None = None
) -> bool:
    """The single fail-closed policy used by HTTP handlers and future workers."""
    if role == Role.ADMINISTRATOR:
        return True
    if action == Action.DOWNLOAD_OWN_ZIP and owner_id != actor_id:
        return False
    if role == Role.OPERATOR:
        return action in _OPERATOR_ACTIONS
    if role == Role.VIEWER:
        return action in _VIEWER_ACTIONS
    return False
