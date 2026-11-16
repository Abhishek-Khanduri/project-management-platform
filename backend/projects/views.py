from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authz import scope
from authz.permissions import PolicyPermission
from tasks.models import Task

from . import services
from .models import Project
from .serializers import AddMemberSerializer, DashboardSerializer, MemberSerializer, ProjectSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="Matches the project name"),
            OpenApiParameter("status", str, enum=["active", "archived"]),
        ]
    )
)
class ProjectViewSet(viewsets.ModelViewSet):
    """
    /api/projects/                              GET list, POST create
    /api/projects/{id}/                         GET, PUT, PATCH, DELETE
    /api/projects/{id}/members/                 GET list, POST add (by email)
    /api/projects/{id}/members/{user_id}/       DELETE remove
    """

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, PolicyPermission]
    # Which policy protects each action (checked by PolicyPermission on get_object()).
    policy_actions = {
        "retrieve": "project.view",
        "update": "project.update",
        "partial_update": "project.update",
        "destroy": "project.delete",
        "members": "project.view",
        "add_member": "project.manage_members",
        "remove_member": "project.manage_members",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # Swagger schema generation has no real user
            return Project.objects.none()
        queryset = Project.objects.select_related("owner").annotate(
            member_count=Count("memberships", distinct=True),
            task_count=Count("tasks", distinct=True),
        )
        # Only projects the user is a member of. Anyone else gets 404, not 403,
        # so we do not reveal that the project exists.
        queryset = scope(self.request.user, "project.view", queryset)

        params = self.request.query_params
        if params.get("search"):
            queryset = queryset.filter(name__icontains=params["search"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        # Explicit order: Django ignores Meta.ordering on queries with Count(),
        # and pagination needs a stable order.
        return queryset.order_by("-created_at", "-id")

    def create(self, request):
        # Any logged-in user may create a project and becomes its owner.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = services.create_project(owner=request.user, **serializer.validated_data)
        # Re-read through get_queryset() so the response includes the counts.
        output = self.get_serializer(self.get_queryset().get(pk=project.pk))
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], serializer_class=MemberSerializer)
    def members(self, request, pk=None):
        project = self.get_object()
        memberships = project.memberships.select_related("user", "project").order_by("joined_at")
        return Response(MemberSerializer(memberships, many=True).data)

    @members.mapping.post
    def add_member(self, request, pk=None):
        project = self.get_object()
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_member(project, serializer.validated_data["email"])
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>\d+)")
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        services.remove_member(project, int(user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses=DashboardSerializer)
@api_view(["GET"])
def dashboard(request):
    """Statistics across every project the current user is a member of."""
    projects = scope(request.user, "project.view", Project.objects.all())
    project_stats = projects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Project.Status.ACTIVE)),
    )
    task_stats = Task.objects.filter(project__in=projects).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=Task.Status.COMPLETED)),
    )
    stats = {
        "total_projects": project_stats["total"],
        "active_projects": project_stats["active"],
        "total_tasks": task_stats["total"],
        "completed_tasks": task_stats["completed"],
        "pending_tasks": task_stats["total"] - task_stats["completed"],
    }
    return Response(DashboardSerializer(stats).data)
