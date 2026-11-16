"""
Business logic for projects. Views call these functions; they never touch
membership rows directly. Authorization has already happened in the view.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from core.exceptions import Conflict
from tasks.models import Task

from .models import Project, ProjectMembership

User = get_user_model()


@transaction.atomic
def create_project(owner, **fields):
    """Create a project; its owner automatically becomes its first member."""
    project = Project.objects.create(owner=owner, **fields)
    ProjectMembership.objects.create(project=project, user=owner)
    return project


def add_member(project, email):
    user = User.objects.filter(email=email.lower()).first()
    if user is None:
        raise NotFound("No user with this email exists.")
    if ProjectMembership.objects.filter(project=project, user=user).exists():
        raise Conflict("This user is already a member of the project.")
    return ProjectMembership.objects.create(project=project, user=user)


@transaction.atomic
def remove_member(project, user_id):
    if project.owner_id == user_id:
        raise ValidationError({"user": ["The project owner cannot be removed."]})
    deleted, _ = ProjectMembership.objects.filter(project=project, user_id=user_id).delete()
    if not deleted:
        raise NotFound("This user is not a member of the project.")
    # Someone outside the project should not stay assigned to its tasks.
    Task.objects.filter(project=project, assignee_id=user_id).update(assignee=None)
