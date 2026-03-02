from django.urls import path

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
    path("cancel/run/<pk>", views.cancel_run_jobs, name="cancel_run_jobs"),
    path("queue/run/<pk>", views.queue_existing_run, name="queue_existing_run"),
    path("cancel/pipeline/<pk>", views.cancel_pipeline_jobs, name="cancel_pipeline_jobs"),
    path("delete/raw/<pk>", views.delete_raw_file, name="delete_raw_file"),
    path("queue/raw/<pk>", views.queue_missing_raw_run, name="queue_missing_raw_run"),
    path(
        "queue-missing/pipeline/<pk>",
        views.queue_missing_pipeline_runs,
        name="queue_missing_runs",
    ),
    path("run/<pk>", views.ResultDetailView.as_view(), name="mq_detail"),
    path("upload/raw/<pk>", views.UploadRaw.as_view(), name="upload_raw"),
    path("basic-upload/", views.UploadRaw.as_view(), name="basic_upload"),
]
