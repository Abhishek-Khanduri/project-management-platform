from rest_framework.permissions import BasePermission

from .engine import authorize


class PolicyPermission(BasePermission):
    """
    Connects DRF views to the policy engine.

    A view declares which policy protects each of its actions, e.g.

        policy_actions = {"retrieve": "project.view", "destroy": "project.delete"}

    DRF calls has_object_permission() inside view.get_object(), so the check runs
    automatically on the loaded object and the view itself contains no permission code.
    """

    def has_object_permission(self, request, view, obj):
        action = view.policy_actions.get(view.action)
        if action:
            authorize(request.user, action, obj)
        return True
