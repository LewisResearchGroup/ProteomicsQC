from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("P/", include(("project.urls", "project"), namespace="project")),
    path("proteomics/", include(("maxquant.urls", "maxquant"), namespace="maxquant")),
    path("dashboard/", include(("dashboards.urls", "dashboards"), namespace="dash")),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
    path("api/", include(("api.urls", "api"), namespace="api")),
    path("user/", include(("user.urls", "user"), namespace="user")),
]

admin.site.site_title = settings.HOME_TITLE
admin.site.site_header = settings.HOME_TITLE
