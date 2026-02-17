from django.urls import path

from .views import HealthView, HomeView, WorkspaceView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("health", HealthView.as_view(), name="health"),
    path("app", HomeView.as_view(), name="app-home"),
    path("app/projects/<uuid:project_id>", WorkspaceView.as_view(), name="workspace"),
]
