from django.urls import path

from . import views

urlpatterns = [
    path("projects", views.ProjectNames.as_view(), name="projects"),
    path("mq/pipelines", views.MaxQuantPipelineNames.as_view(), name="mq-pipelines"),
    path("mq/qc-data", views.QcDataAPI.as_view(), name="qc-data"),
    path("mq/protein-names", views.ProteinNamesAPI.as_view(), name="protein-names"),
    path("mq/protein-groups", views.ProteinGroupsAPI.as_view(), name="protein-groups"),
    path("upload/raw", views.RawFileUploadAPI.as_view(), name="upload-raw"),
    path("flag/create", views.CreateFlag.as_view(), name="create-flag"),
    path("flag/delete", views.DeleteFlag.as_view(), name="delete-flag"),
]
