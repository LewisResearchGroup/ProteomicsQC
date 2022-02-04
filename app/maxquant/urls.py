from django.urls import path, re_path, include

from . import views

urlpatterns = [
    path(
        "detail/<slug:project>/<slug:pipeline>",
        views.maxquant_pipeline_view,
        name="detail",
    ),
    ## download concatenated MaxQuant files in csv format
    path(
        "download/pipeline/<pk>",
        views.pipeline_download_file,
        name="pipeline-download-file",
    ),
    ## download zipped files for one specific .RAW file
    path("download/run/<pk>", views.maxquant_download, name="download_run"),
    path("run/<pk>", views.ResultDetailView.as_view(), name="mq_detail"),
    path("upload/raw/<pk>", views.UploadRaw.as_view(), name="upload_raw"),
    path("basic-upload/", views.UploadRaw.as_view(), name="basic_upload"),
]
