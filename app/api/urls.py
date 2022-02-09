from django.urls import path

from . import views

urlpatterns = [
    path("projects", views.ProjectNames.as_view(), name="projects"),
    path("pipelines", views.PipelineNames.as_view(), name="mq-pipelines"),
    path("qc-data", views.QcDataAPI.as_view(), name="qc-data"),
    path("protein-names", views.ProteinNamesAPI.as_view(), name="protein-names"),
    path("protein-groups", views.ProteinGroupsAPI.as_view(), name="protein-groups"),
    path("upload/raw", views.RawFileUploadAPI.as_view(), name="upload-raw"),
    #path("flag/create", views.CreateFlag.as_view(), name="create-flag"),
    #path("flag/delete", views.DeleteFlag.as_view(), name="delete-flag"),
    path("rawfile", views.RawFile.as_view(), name="modify-raw-file"),
]
