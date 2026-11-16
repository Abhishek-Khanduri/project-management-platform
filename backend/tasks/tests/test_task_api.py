import pytest

from projects.models import ProjectMembership
from projects.services import create_project
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
    project = create_project(owner=owner, name="Website")
    ProjectMembership.objects.create(project=project, user=member)
    return project


@pytest.fixture
def task(project, member):
    return Task.objects.create(project=project, title="Fix login", created_by=member)


def tasks_url(project):
    return f"/api/projects/{project.id}/tasks/"


def task_url(task):
    return f"/api/tasks/{task.id}/"


COMPLETE_FIELDS = {"description": "Steps to reproduce", "due_date": "2026-12-01"}


# --- Create -----------------------------------------------------------------


def test_member_can_create_task(auth_client, project, member):
    response = auth_client(member).post(
        tasks_url(project), {"title": "Write docs", "priority": "high", "assignee_id": member.id}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "todo"
    assert body["priority"] == "high"
    assert body["created_by"]["email"] == "member@example.com"
    assert body["assignee"]["email"] == "member@example.com"


def test_non_member_cannot_create_task(auth_client, project, outsider):
    response = auth_client(outsider).post(tasks_url(project), {"title": "Sneaky"})

    assert response.status_code == 404


def test_create_task_validates_input(auth_client, project, member):
    response = auth_client(member).post(tasks_url(project), {"title": "", "priority": "urgent"})

    assert response.status_code == 400
    assert {"title", "priority"} <= response.json()["error"]["details"].keys()


def test_assignee_must_be_project_member(auth_client, project, member, outsider):
    response = auth_client(member).post(tasks_url(project), {"title": "T", "assignee_id": outsider.id})

    assert response.status_code == 400
    assert "assignee_id" in response.json()["error"]["details"]


# --- List, search, filter, paginate -----------------------------------------


def test_list_search_filter_and_paginate(auth_client, project, member):
    Task.objects.create(project=project, title="Login bug", priority="high", created_by=member)
    Task.objects.create(project=project, title="Signup page", description="login link", created_by=member)
    Task.objects.create(project=project, title="Footer", status="in_progress", created_by=member)
    client = auth_client(member)

    assert client.get(tasks_url(project), {"search": "login"}).json()["count"] == 2
    assert client.get(tasks_url(project), {"priority": "high"}).json()["count"] == 1
    assert client.get(tasks_url(project), {"status": "in_progress"}).json()["count"] == 1

    page = client.get(tasks_url(project), {"page_size": 2}).json()
    assert page["count"] == 3
    assert len(page["results"]) == 2
    assert page["next"] is not None


def test_non_member_cannot_list_tasks(auth_client, project, outsider):
    assert auth_client(outsider).get(tasks_url(project)).status_code == 404


def test_non_member_cannot_view_task(auth_client, task, outsider):
    assert auth_client(outsider).get(task_url(task)).status_code == 404


# --- Update -----------------------------------------------------------------


def test_creator_can_update_task(auth_client, task, member):
    response = auth_client(member).patch(task_url(task), {"title": "Fix login page", "status": "in_progress"})

    assert response.status_code == 200
    assert response.json()["title"] == "Fix login page"


def test_member_who_is_not_creator_or_assignee_cannot_update(auth_client, task, owner):
    response = auth_client(owner).patch(task_url(task), {"title": "Changed"})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Only the task's creator or assignee can update it."


# --- Completion -------------------------------------------------------------


def test_cannot_complete_task_without_required_fields(auth_client, task, member):
    response = auth_client(member).patch(task_url(task), {"status": "completed"})

    assert response.status_code == 403
    task.refresh_from_db()
    assert task.status == "todo"


def test_can_complete_task_once_required_fields_are_set(auth_client, task, member):
    # Setting the assignee and completing in the same request is allowed.
    response = auth_client(member).patch(
        task_url(task), {"status": "completed", "assignee_id": member.id, **COMPLETE_FIELDS}
    )

    assert response.status_code == 200
    assert response.json()["completed_at"] is not None


def test_reopening_task_clears_completed_at(auth_client, task, member):
    client = auth_client(member)
    client.patch(task_url(task), {"status": "completed", "assignee_id": member.id, **COMPLETE_FIELDS})

    response = client.patch(task_url(task), {"status": "in_progress"})

    assert response.json()["completed_at"] is None


# --- Delete -----------------------------------------------------------------


def test_owner_can_delete_todo_task(auth_client, task, owner):
    response = auth_client(owner).delete(task_url(task))

    assert response.status_code == 204
    assert not Task.objects.filter(id=task.id).exists()


def test_owner_cannot_delete_in_progress_task(auth_client, task, owner):
    task.status = "in_progress"
    task.save()

    response = auth_client(owner).delete(task_url(task))

    assert response.status_code == 403


def test_creator_who_is_not_owner_cannot_delete(auth_client, task, member):
    assert auth_client(member).delete(task_url(task)).status_code == 403


# --- Dashboard --------------------------------------------------------------


def test_dashboard_counts_only_my_projects(auth_client, project, owner, member, outsider):
    create_project(owner=owner, name="Old", status="archived")
    Task.objects.create(project=project, title="A", status="completed", created_by=member)
    Task.objects.create(project=project, title="B", created_by=member)
    other = create_project(owner=outsider, name="Not mine")
    Task.objects.create(project=other, title="C", created_by=outsider)

    response = auth_client(owner).get("/api/dashboard/")

    assert response.status_code == 200
    assert response.json() == {
        "total_projects": 2,
        "active_projects": 1,
        "total_tasks": 2,
        "completed_tasks": 1,
        "pending_tasks": 1,
    }
