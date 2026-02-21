from django.shortcuts import render
from django.conf import settings as conf_settings
from django.db.models import Count, Q
from django.urls import reverse, NoReverseMatch

from project.models import Project
from maxquant.models import Result, Pipeline


def home(request):
    context = {"home_title": conf_settings.HOME_TITLE}
    if request.user.is_authenticated:
        projects_qs = Project.objects.all()
        if not (request.user.is_staff or request.user.is_superuser):
            projects_qs = projects_qs.filter(
                Q(created_by_id=request.user.id) | Q(users=request.user)
            ).distinct()

        project_count = projects_qs.count()
        pipeline_count = (
            projects_qs.aggregate(total=Count("pipeline", distinct=True)).get("total", 0)
            or 0
        )

        recent_runs_qs = (
            Result.objects.select_related("raw_file__pipeline__project")
            .filter(raw_file__pipeline__project__in=projects_qs)
            .order_by("-created")[:3]
        )
        latest_run = recent_runs_qs[0] if recent_runs_qs else None
        latest_pipeline = (
            Pipeline.objects.select_related("project")
            .filter(project__in=projects_qs)
            .order_by("-created")
            .first()
        )
        latest_project = projects_qs.order_by("-created").first()
        recent_runs = []
        for run in recent_runs_qs:
            pipeline = run.raw_file.pipeline
            project = pipeline.project
            recent_runs.append(
                {
                    "name": run.name,
                    "status": run.overall_status,
                    "project_name": project.name,
                    "pipeline_name": pipeline.name,
                    "url": run.url,
                }
            )

        active_runs = 0
        for run in recent_runs_qs:
            if run.overall_status in {"queued", "running"}:
                active_runs += 1

        try:
            admin_project_add_url = reverse("admin:project_project_add")
        except NoReverseMatch:
            admin_project_add_url = reverse("admin:index")

        try:
            admin_pipeline_add_url = reverse("admin:maxquant_pipeline_add")
        except NoReverseMatch:
            admin_pipeline_add_url = reverse("admin:index")

        step_1_url = reverse("project:list")
        step_1_note = "Browse project spaces and counts."
        if project_count == 0 and request.user.is_staff:
            step_1_url = admin_project_add_url
            step_1_note = "No projects yet. Create your first project."
        elif project_count == 0:
            step_1_note = "No projects are available yet. Contact an administrator."

        step_2_url = reverse("project:list")
        step_2_note = "Open a project and pick a pipeline."
        if latest_project is not None:
            step_2_url = latest_project.url
            step_2_note = f"Continue in {latest_project.name}."

        step_3_url = reverse("project:list")
        step_3_note = "Open a pipeline to upload files."
        if latest_pipeline is not None:
            step_3_url = latest_pipeline.url
            step_3_note = f"Open {latest_pipeline.project.name} / {latest_pipeline.name} upload queue."
        elif request.user.is_staff:
            step_3_url = admin_pipeline_add_url
            step_3_note = "No pipelines yet. Create one to start uploads."

        step_4_url = reverse("project:list")
        step_4_note = "Open run results and QC plots."
        if latest_run is not None:
            step_4_url = latest_run.url
            step_4_note = f"Resume latest run: {latest_run.name}."
        elif latest_pipeline is not None:
            step_4_url = latest_pipeline.url
            step_4_note = "No runs yet. Open a pipeline and submit files."

        quick_steps = [
            {
                "index": 1,
                "title": "Open projects",
                "note": step_1_note,
                "url": step_1_url,
            },
            {
                "index": 2,
                "title": "Select pipeline",
                "note": step_2_note,
                "url": step_2_url,
            },
            {
                "index": 3,
                "title": "Upload .raw files",
                "note": step_3_note,
                "url": step_3_url,
            },
            {
                "index": 4,
                "title": "Open run results",
                "note": step_4_note,
                "url": step_4_url,
            },
        ]

        context.update(
            {
                "project_count": project_count,
                "pipeline_count": pipeline_count,
                "active_runs": active_runs,
                "recent_runs": recent_runs,
                "quick_steps": quick_steps,
            }
        )
    return render(request, "home.html", context)
