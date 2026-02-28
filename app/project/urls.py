from django.urls import path

from . import views

urlpatterns = [
    path("project-list/", views.ProjectListView.as_view(), name="list"),
    path("project-detail/<slug>", views.project_detail_view, name="detail"),
    path(
        "project-detail/<slug>/download-pipelines",
        views.project_pipelines_download,
        name="download_pipelines",
    ),
]
