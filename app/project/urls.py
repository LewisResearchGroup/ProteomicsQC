from django.urls import path, re_path, include

from . import views

urlpatterns = [
    path("project-list/", views.ProjectListView.as_view(), name="list"),
    path("project-detail/<slug>", views.project_detail_view, name="detail"),
]
