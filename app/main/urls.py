from django.contrib import admin
from django.urls import path,  re_path, include
from django.conf import settings

from . import views

urlpatterns = [
    path('', views.home, name='home' ),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls'), {'extra_context': {'home_title': settings.HOME_TITLE}}),
    #path('o/', include('oauth2_provider.urls',  namespace='oauth2_provider')),
    path('P/', include(('project.urls', 'project'),  namespace='project')),
    path('d/', include(('dashboards.urls', 'dashboards'), namespace='dash')),
]

