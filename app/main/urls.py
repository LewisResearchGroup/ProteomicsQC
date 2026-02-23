from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/login/", views.login_redirect, name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("P/", include(("project.urls", "project"), namespace="project")),
    path("proteomics/", include(("maxquant.urls", "maxquant"), namespace="maxquant")),
    path("dashboard/", include(("dashboards.urls", "dashboards"), namespace="dash")),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
    path("api/", include(("api.urls", "api"), namespace="api")),
    path("user/", include(("user.urls", "user"), namespace="user")),
    # Fix Dash asset lookup: some versions request plotly.min.js without package_data/
    path(
        "static/dash/component_data/plotly.min.js",
        RedirectView.as_view(
            url="/static/dash/component_data/plotly/package_data/plotly.min.js"
        ),
    ),
    path(
        "static/dash/component/plotly/package_data/plotly.min.js",
        RedirectView.as_view(
            url="/static/dash/component_data/plotly/package_data/plotly.min.js"
        ),
    ),
]

admin.site.site_title = settings.HOME_TITLE
admin.site.site_header = settings.HOME_TITLE

# Serve static/media files directly from Django (suitable for local/docker without nginx)
urlpatterns += staticfiles_urlpatterns()
if settings.MEDIA_URL:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
