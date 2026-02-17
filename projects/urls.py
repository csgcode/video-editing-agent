from django.urls import path

from .views import (
    DraftDetailView,
    DraftGenerateView,
    ExportCreateView,
    JobDetailView,
    ProjectArtifactsView,
    ProjectAssetUploadView,
    ProjectCreateView,
)

urlpatterns = [
    path("projects", ProjectCreateView.as_view(), name="project-create"),
    path("projects/<uuid:project_id>/assets", ProjectAssetUploadView.as_view(), name="project-asset-upload"),
    path("projects/<uuid:project_id>/drafts/generate", DraftGenerateView.as_view(), name="draft-generate"),
    path("jobs/<uuid:job_id>", JobDetailView.as_view(), name="job-detail"),
    path("projects/<uuid:project_id>/draft", DraftDetailView.as_view(), name="draft-detail-update"),
    path("projects/<uuid:project_id>/export", ExportCreateView.as_view(), name="export-create"),
    path("projects/<uuid:project_id>/artifacts", ProjectArtifactsView.as_view(), name="artifacts-list"),
]
