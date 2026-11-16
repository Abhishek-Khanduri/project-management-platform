"""
Business logic for tasks. Authorization for the request itself (create/update)
has already happened in the view; here we only add the completion rule, because
it depends on what the task will look like after the change.
"""
from django.utils import timezone

from authz import authorize

from .models import Task


def create_task(user, project, **fields):
    task = Task(project=project, created_by=user, **fields)
    _handle_status_change(user, task, was_completed=False)
    task.save()
    return task


def update_task(user, task, **changes):
    was_completed = task.status == Task.Status.COMPLETED
    for field, value in changes.items():
        setattr(task, field, value)
    _handle_status_change(user, task, was_completed)
    task.save()
    return task


def _handle_status_change(user, task, was_completed):
    is_completed = task.status == Task.Status.COMPLETED
    if is_completed and not was_completed:
        # Checked on the task with the new values applied, before anything is saved.
        authorize(user, "task.complete", task)
        task.completed_at = timezone.now()
    elif was_completed and not is_completed:
        task.completed_at = None
