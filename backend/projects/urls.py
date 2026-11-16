from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ProjectViewSet, dashboard

router = SimpleRouter()
router.register("projects", ProjectViewSet, basename="project")

urlpatterns = [path("dashboard/", dashboard, name="dashboard"), *router.urls]
