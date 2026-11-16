"""One test per rule in the assignment, checking both the allowed and the denied side."""
from datetime import date

import pytest
from rest_framework.exceptions import PermissionDenied

from authz import authorize, can, scope
from projects.models import Project, ProjectMembership
from tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(make_user):
    return make_user("owner@example.com")


@pytest.fixture
def member(make_user):
    return make_user("member@example.com")


@pytest.fixture
def outsider(make_user):
    return make_user("outsider@example.com")


@pytest.fixture
def project(owner, member):
    project = Project.objects.create(name="Website", owner=owner)
    ProjectMembership.objects.create(project=project, user=owner)
    ProjectMembership.objects.create(project=project, user=member)
    return project


@pytest.fixture
def make_task(project, member):
    def _make_task(**fields):
        return Task.objects.create(project=project, title="Fix login", created_by=member, **fields)

    return _make_task


# --- Project visibility -----------------------------------------------------


def test_members_can_view_project(project, owner, member):
    assert can(owner, "project.view", project)
    assert can(member, "project.view", project)


def test_non_member_cannot_view_project(project, outsider):
    assert not can(outsider, "project.view", project)


def test_project_list_only_contains_own_projects(project, outsider):
    Project.objects.create(name="Other", owner=outsider)

    assert list(scope(outsider, "project.view", Project.objects.all())) == []
    assert list(scope(project.owner, "project.view", Project.objects.all())) == [project]


# --- Project update / delete / members --------------------------------------


@pytest.mark.parametrize("action", ["project.update", "project.delete", "project.manage_members"])
def test_only_owner_can_change_project(action, project, owner, member):
    assert can(owner, action, project)
    assert not can(member, action, project)


# --- Task creation ----------------------------------------------------------


def test_only_members_can_create_tasks(project, member, outsider):
    assert can(member, "task.create", project)
    assert not can(outsider, "task.create", project)


# --- Task update ------------------------------------------------------------


def test_creator_can_update_task(make_task, member):
    assert can(member, "task.update", make_task())


def test_assignee_can_update_task(make_task, project, make_user):
    assignee = make_user("assignee@example.com")
    ProjectMembership.objects.create(project=project, user=assignee)

    assert can(assignee, "task.update", make_task(assignee=assignee))


def test_other_members_cannot_update_task(make_task, owner):
    # Even the project owner cannot edit a task they neither created nor are assigned to.
    assert not can(owner, "task.update", make_task())


def test_creator_removed_from_project_cannot_update_task(make_task, project, member):
    task = make_task()
    ProjectMembership.objects.filter(project=project, user=member).delete()

    assert not can(member, "task.update", task)


# --- Task delete ------------------------------------------------------------


def test_owner_can_delete_todo_task(make_task, owner):
    assert can(owner, "task.delete", make_task(status="todo"))


@pytest.mark.parametrize("status", ["in_progress", "completed"])
def test_owner_cannot_delete_task_that_is_not_todo(status, make_task, owner):
    assert not can(owner, "task.delete", make_task(status=status))


def test_non_owner_cannot_delete_todo_task(make_task, member):
    assert not can(member, "task.delete", make_task(status="todo"))


# --- Task completion --------------------------------------------------------


def test_task_with_all_required_fields_can_be_completed(make_task, member):
    task = make_task(assignee=member, description="Details", due_date=date(2026, 12, 1))

    assert can(member, "task.complete", task)


@pytest.mark.parametrize(
    "missing",
    [
        {"assignee": None},
        {"description": ""},
        {"due_date": None},
    ],
)
def test_task_missing_required_fields_cannot_be_completed(missing, make_task, member):
    fields = {"assignee": member, "description": "Details", "due_date": date(2026, 12, 1), **missing}

    assert not can(member, "task.complete", make_task(**fields))


# --- The engine itself ------------------------------------------------------


def test_authorize_raises_403_with_policy_message(project, outsider):
    with pytest.raises(PermissionDenied) as error:
        authorize(outsider, "project.view", project)

    assert str(error.value.detail) == "You are not a member of this project."


def test_unknown_action_is_an_error_not_an_allow(project, owner):
    with pytest.raises(ValueError):
        can(owner, "project.destroy_everything", project)
