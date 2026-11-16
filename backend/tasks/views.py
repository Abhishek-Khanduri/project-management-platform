from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from authz import authorize, scope
from authz.permissions import PolicyPermission
from projects.models import Project

from . import services
from .models import Task
from .serializers import TaskSerializer


def filter_tasks(queryset, params):
    """?search=  ?status=  ?priority=  ?assignee=<user id>"""
    if params.get("search"):
        term = params["search"]
        queryset = queryset.filter(Q(title__icontains=term) | Q(description__icontains=term))
    if params.get("status"):
        queryset = queryset.filter(status=params["status"])
    if params.get("priority"):
        queryset = queryset.filter(priority=params["priority"])
    if params.get("assignee", "").isdigit():
        queryset = queryset.filter(assignee_id=params["assignee"])
    return queryset


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="Matches the title or description"),
            OpenApiParameter("status", str, enum=["todo", "in_progress", "completed"]),
            OpenApiParameter("priority", str, enum=["low", "medium", "high"]),
            OpenApiParameter("assignee", int, description="Assignee's user id"),
        ]
    )
)
class ProjectTaskViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    /api/projects/{project_id}/tasks/    GET list (search, filter, paginate), POST create
    """

    serializer_class = TaskSerializer

    def get_project(self):
        # 404 if the project does not exist or the user is not a member.
        visible = scope(self.request.user, "project.view", Project.objects.all())
        return get_object_or_404(visible, pk=self.kwargs["project_id"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # Swagger schema generation has no real request
            return Task.objects.none()
        project = self.get_project()
        queryset = project.tasks.select_related("assignee", "created_by")
        return filter_tasks(queryset, self.request.query_params)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create" and not getattr(self, "swagger_fake_view", False):
            context["project"] = self.get_project()
        return context

    def perform_create(self, serializer):
        project = serializer.context["project"]
        authorize(self.request.user, "task.create", project)
        serializer.instance = services.create_task(self.request.user, project, **serializer.validated_data)


class TaskViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """
    /api/tasks/{id}/    GET, PUT, PATCH, DELETE
    """

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, PolicyPermission]
    policy_actions = {
        "retrieve": "task.view",
        "update": "task.update",
        "partial_update": "task.update",
        "destroy": "task.delete",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # Swagger schema generation has no real user
            return Task.objects.none()
        # Tasks in projects the user is not a member of give 404.
        queryset = Task.objects.select_related("project", "assignee", "created_by")
        return scope(self.request.user, "task.view", queryset)

    def perform_update(self, serializer):
        serializer.instance = services.update_task(
            self.request.user, serializer.instance, **serializer.validated_data
        )
