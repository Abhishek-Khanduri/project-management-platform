import pytest

from projects.models import Project, ProjectMembership
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
    project = create_project(owner=owner, name="Website", description="Company site")
    ProjectMembership.objects.create(project=project, user=member)
    return project


def url(project=None, suffix=""):
    return f"/api/projects/{project.id}/{suffix}" if project else "/api/projects/"


# --- Create / list / retrieve -----------------------------------------------


def test_create_project_makes_creator_owner_and_member(auth_client, owner):
    response = auth_client(owner).post(url(), {"name": "Mobile app"})

    assert response.status_code == 201
    body = response.json()
    assert body["owner"]["email"] == "owner@example.com"
    assert body["member_count"] == 1
    assert body["status"] == "active"
    assert ProjectMembership.objects.filter(project_id=body["id"], user=owner).exists()


def test_create_project_requires_name(auth_client, owner):
    response = auth_client(owner).post(url(), {"description": "No name"})

    assert response.status_code == 400
    assert "name" in response.json()["error"]["details"]


def test_list_returns_only_my_projects_with_counts(auth_client, project, member, outsider):
    create_project(owner=outsider, name="Secret")

    response = auth_client(member).get(url())

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["name"] == "Website"
    assert body["results"][0]["member_count"] == 2


def test_list_supports_search_and_status_filter(auth_client, owner, project):
    create_project(owner=owner, name="Archived thing", status="archived")
    client = auth_client(owner)

    assert client.get(url(), {"search": "web"}).json()["count"] == 1
    assert client.get(url(), {"status": "archived"}).json()["results"][0]["name"] == "Archived thing"


def test_non_member_gets_404_for_project(auth_client, project, outsider):
    response = auth_client(outsider).get(url(project))

    assert response.status_code == 404


def test_permissions_field_reflects_policies(auth_client, project, owner, member):
    as_owner = auth_client(owner).get(url(project)).json()["permissions"]
    as_member = auth_client(member).get(url(project)).json()["permissions"]

    assert as_owner == {"can_update": True, "can_delete": True, "can_manage_members": True}
    assert as_member == {"can_update": False, "can_delete": False, "can_manage_members": False}


# --- Update / delete --------------------------------------------------------


def test_owner_can_update_project(auth_client, project, owner):
    response = auth_client(owner).patch(url(project), {"name": "New name", "status": "archived"})

    assert response.status_code == 200
    assert response.json()["name"] == "New name"
    assert response.json()["status"] == "archived"


def test_member_cannot_update_project(auth_client, project, member):
    response = auth_client(member).patch(url(project), {"name": "Hacked"})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Only the project owner can update this project."


def test_invalid_status_is_rejected(auth_client, project, owner):
    response = auth_client(owner).patch(url(project), {"status": "deleted"})

    assert response.status_code == 400


def test_owner_can_delete_project(auth_client, project, owner):
    response = auth_client(owner).delete(url(project))

    assert response.status_code == 204
    assert not Project.objects.filter(id=project.id).exists()


def test_member_cannot_delete_project(auth_client, project, member):
    response = auth_client(member).delete(url(project))

    assert response.status_code == 403


# --- Members ----------------------------------------------------------------


def test_members_can_list_members(auth_client, project, member):
    response = auth_client(member).get(url(project, "members/"))

    assert response.status_code == 200
    assert [(m["email"], m["is_owner"]) for m in response.json()] == [
        ("owner@example.com", True),
        ("member@example.com", False),
    ]


def test_owner_can_add_member_by_email(auth_client, project, owner, outsider):
    response = auth_client(owner).post(url(project, "members/"), {"email": "Outsider@example.com"})

    assert response.status_code == 201
    assert ProjectMembership.objects.filter(project=project, user=outsider).exists()


def test_adding_existing_member_returns_409(auth_client, project, owner):
    response = auth_client(owner).post(url(project, "members/"), {"email": "member@example.com"})

    assert response.status_code == 409


def test_adding_unknown_email_returns_404(auth_client, project, owner):
    response = auth_client(owner).post(url(project, "members/"), {"email": "nobody@example.com"})

    assert response.status_code == 404


def test_member_cannot_add_members(auth_client, project, member, outsider):
    response = auth_client(member).post(url(project, "members/"), {"email": "outsider@example.com"})

    assert response.status_code == 403


def test_owner_can_remove_member_and_their_tasks_are_unassigned(auth_client, project, owner, member):
    task = Task.objects.create(project=project, title="T", created_by=owner, assignee=member)

    response = auth_client(owner).delete(url(project, f"members/{member.id}/"))

    assert response.status_code == 204
    assert not ProjectMembership.objects.filter(project=project, user=member).exists()
    task.refresh_from_db()
    assert task.assignee is None


def test_owner_cannot_be_removed(auth_client, project, owner):
    response = auth_client(owner).delete(url(project, f"members/{owner.id}/"))

    assert response.status_code == 400


def test_removing_non_member_returns_404(auth_client, project, owner, outsider):
    response = auth_client(owner).delete(url(project, f"members/{outsider.id}/"))

    assert response.status_code == 404
