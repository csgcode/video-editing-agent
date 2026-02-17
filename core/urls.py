from django.urls import path

from .views import HealthView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("health", HealthView.as_view(), name="health"),
]
