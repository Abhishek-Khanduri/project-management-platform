"""
The single entry point for authorization decisions.

Views call   authorize(request.user, "task.delete", task)
and never check permissions themselves.
"""
import logging

from rest_framework.exceptions import PermissionDenied

from .policies import POLICIES, SCOPES

logger = logging.getLogger(__name__)


def can(user, action, resource):
    """Return True if `user` may perform `action` on `resource`."""
    if action not in POLICIES:
        # Deny by default: a typo in an action name must never grant access.
        raise ValueError(f"No policy defined for action '{action}'.")
    policy, _message = POLICIES[action]
    return policy(user, resource)


def authorize(user, action, resource):
    """Like can(), but raises PermissionDenied (HTTP 403) with the policy's message."""
    if not can(user, action, resource):
        logger.info("Denied %s for user=%s on %r", action, user.id, resource)
        raise PermissionDenied(POLICIES[action][1])


def scope(user, action, queryset):
    """Filter a queryset down to the rows `user` may perform `action` on."""
    if action not in SCOPES:
        raise ValueError(f"No scope defined for action '{action}'.")
    # distinct(): the membership join could otherwise return a row more than once.
    return SCOPES[action](user, queryset).distinct()
