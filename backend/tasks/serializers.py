from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import UserSerializer
from authz import can

from .models import Task

User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    # Read: full user objects. Write: just the user id ("assignee_id": 5 or null).
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee", queryset=User.objects.all(), allow_null=True, required=False, write_only=True
    )
    created_by = UserSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "project", "title", "description", "status", "priority",
            "assignee", "assignee_id", "created_by", "due_date", "completed_at",
            "permissions", "created_at", "updated_at",
        ]
        read_only_fields = ["project", "completed_at", "created_at", "updated_at"]

    def validate_assignee_id(self, user):
        # On create the view passes the project in the context; on update it is the task's project.
        project = self.instance.project if self.instance else self.context["project"]
        if user is not None and not project.memberships.filter(user=user).exists():
            raise serializers.ValidationError("The assignee must be a member of the project.")
        return user

    def get_permissions(self, task) -> dict:
        user = self.context["request"].user
        return {
            "can_update": can(user, "task.update", task),
            "can_delete": can(user, "task.delete", task),
        }
