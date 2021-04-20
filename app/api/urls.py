from django.urls import path

from . import views

urlpatterns = [
    path('projects', views.ProjectNames.as_view(), name='api-all-projects'),
    path('mq/pipelines', views.MaxQuantPipelineNames.as_view(), name='api-prot-pipelines'),
    path('qc/data', views.QcDataAPI.as_view(), name='api-data'),
]

