from rest_framework.routers import SimpleRouter

from .views import ProjectTaskViewSet, TaskViewSet

router = SimpleRouter()
router.register(r"projects/(?P<project_id>\d+)/tasks", ProjectTaskViewSet, basename="project-task")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
