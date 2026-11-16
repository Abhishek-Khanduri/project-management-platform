"""
Every authorization rule in the application lives in this file.

A policy is a small function: (user, resource) -> True/False.
It looks only at attributes of the user and the resource (who owns the project,
who created the task, what status the task has...). There are no roles.

To add or change a rule, edit this file only; views never contain permission checks.
"""

# ---------------------------------------------------------------------------
# Facts about a user and a project, reused by the policies below.
# ---------------------------------------------------------------------------


def is_project_member(user, project):
    return project.memberships.filter(user=user).exists()


def is_project_owner(user, project):
    return project.owner_id == user.id


# ---------------------------------------------------------------------------
# Project policies (resource = a Project)
# ---------------------------------------------------------------------------


def can_view_project(user, project):
    return is_project_member(user, project)


def can_update_project(user, project):
    return is_project_owner(user, project)


def can_delete_project(user, project):
    return is_project_owner(user, project)


def can_manage_members(user, project):
    # The assignment does not say who may add/remove members; we allow the owner only.
    return is_project_owner(user, project)


# ---------------------------------------------------------------------------
# Task policies (resource = a Task, except task.create where it is the Project)
# ---------------------------------------------------------------------------

# Fields a task must have filled in before it can be marked Completed.
REQUIRED_FOR_COMPLETION = ["title", "description", "due_date", "assignee_id"]


def can_create_task(user, project):
    return is_project_member(user, project)


def can_view_task(user, task):
    return is_project_member(user, task.project)


def can_update_task(user, task):
    # Must still be in the project, and be the creator or the assignee.
    is_creator_or_assignee = user.id in (task.created_by_id, task.assignee_id)
    return is_creator_or_assignee and is_project_member(user, task.project)


def can_delete_task(user, task):
    return task.status == "todo" and is_project_owner(user, task.project)


def can_complete_task(user, task):
    # Checked against the task *with the requested changes applied*, so a user can
    # set the assignee and mark it completed in the same request.
    return all(getattr(task, field) for field in REQUIRED_FOR_COMPLETION)


# ---------------------------------------------------------------------------
# The registry: action name -> (policy, message shown when it is denied).
# ---------------------------------------------------------------------------

POLICIES = {
    "project.view": (can_view_project, "You are not a member of this project."),
    "project.update": (can_update_project, "Only the project owner can update this project."),
    "project.delete": (can_delete_project, "Only the project owner can delete this project."),
    "project.manage_members": (can_manage_members, "Only the project owner can add or remove members."),
    "task.create": (can_create_task, "Only project members can create tasks."),
    "task.view": (can_view_task, "You are not a member of this task's project."),
    "task.update": (can_update_task, "Only the task's creator or assignee can update it."),
    "task.delete": (can_delete_task, "Only the project owner can delete a task, and only while it is in Todo."),
    "task.complete": (
        can_complete_task,
        "A task needs an assignee, a description and a due date before it can be completed.",
    ),
}


# ---------------------------------------------------------------------------
# Scopes: the same rules applied to lists, as database filters.
# "A user can only view projects they are a member of" must also hold for
# GET /projects/, so the list is filtered in the query instead of one by one.
# ---------------------------------------------------------------------------


def visible_projects(user, queryset):
    return queryset.filter(memberships__user=user)


def visible_tasks(user, queryset):
    return queryset.filter(project__memberships__user=user)


SCOPES = {
    "project.view": visible_projects,
    "task.view": visible_tasks,
}
