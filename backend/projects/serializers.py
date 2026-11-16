from rest_framework import serializers

from accounts.serializers import UserSerializer
from authz import can

from .models import Project, ProjectMembership


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    # These two come from .annotate() in the view's queryset (one query, no N+1).
    member_count = serializers.IntegerField(read_only=True)
    task_count = serializers.IntegerField(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "status", "owner",
            "member_count", "task_count", "permissions", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_permissions(self, project) -> dict:
        """What the current user may do, so the UI can show/hide buttons. Decided by the same policies."""
        user = self.context["request"].user
        return {
            "can_update": can(user, "project.update", project),
            "can_delete": can(user, "project.delete", project),
            "can_manage_members": can(user, "project.manage_members", project),
        }


class MemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMembership
        fields = ["id", "email", "first_name", "last_name", "is_owner", "joined_at"]

    def get_is_owner(self, membership) -> bool:
        return membership.project.owner_id == membership.user_id


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()


class DashboardSerializer(serializers.Serializer):
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
