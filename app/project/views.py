from django.views.generic import ListView

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q, Max, DateTimeField, Value
from django.db.models.functions import Cast, Coalesce, Greatest
from django.utils import timezone

from .models import Project
from maxquant.models import Pipeline, Result
import csv
import datetime


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    login_url = "/accounts/login/"
    paginate_by = settings.PAGINATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = list(context.get("project_list", []))
        project_ids = [project.pk for project in projects]
        active_runs_by_project = {pk: 0 for pk in project_ids}

        if project_ids:
            results = (
                Result.objects
                .filter(raw_file__pipeline__project_id__in=project_ids)
                .select_related("raw_file__pipeline__project")
            )
            for result in results:
                if result.overall_status in {"queued", "running"}:
                    project_id = result.raw_file.pipeline.project_id
                    active_runs_by_project[project_id] = (
                        active_runs_by_project.get(project_id, 0) + 1
                    )

        for project in projects:
            project.active_runs_count = active_runs_by_project.get(project.pk, 0)

        context["search_query"] = self.request.GET.get("q", "").strip()
        context["activity_filter"] = self.request.GET.get("activity", "all")
        context["pipeline_filter"] = self.request.GET.get("pipeline", "all")
        context["home_title"] = settings.HOME_TITLE
        return context

    def get_queryset(self, *args, **kwargs):
        epoch = timezone.make_aware(datetime.datetime(1970, 1, 1))
        queryset = (
            Project.objects
            .annotate(
                n_pipelines=Count("pipeline", distinct=True),
                n_raw_files=Count("pipeline__rawfile", distinct=True),
                n_members=Count("users", distinct=True),
                project_created_at=Cast("created", output_field=DateTimeField()),
                last_pipeline_created_at=Cast(
                    Max("pipeline__created"), output_field=DateTimeField()
                ),
                last_rawfile_created_at=Cast(
                    Max("pipeline__rawfile__created"), output_field=DateTimeField()
                ),
                last_result_created_at=Max("pipeline__rawfile__result__created"),
            )
            .annotate(
                last_activity=Greatest(
                    Coalesce("project_created_at", Value(epoch)),
                    Coalesce("last_pipeline_created_at", Value(epoch)),
                    Coalesce("last_rawfile_created_at", Value(epoch)),
                    Coalesce("last_result_created_at", Value(epoch)),
                )
            )
        )
        user = self.request.user
        if user.is_staff or user.is_superuser:
            filtered_queryset = queryset
        else:
            filtered_queryset = queryset.filter(
                Q(created_by_id=user.id) | Q(users=user)
            ).distinct()

        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            filtered_queryset = filtered_queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(slug__icontains=search_query)
            )

        pipeline_filter = self.request.GET.get("pipeline", "all")
        if pipeline_filter == "with":
            filtered_queryset = filtered_queryset.filter(n_pipelines__gt=0)
        elif pipeline_filter == "without":
            filtered_queryset = filtered_queryset.filter(n_pipelines=0)

        activity_filter = self.request.GET.get("activity", "all")
        recent_cutoff = timezone.now() - datetime.timedelta(days=30)
        if activity_filter == "recent":
            filtered_queryset = filtered_queryset.filter(last_activity__gte=recent_cutoff)
        elif activity_filter == "stale":
            filtered_queryset = filtered_queryset.filter(last_activity__lt=recent_cutoff)

        return filtered_queryset.order_by("-last_activity", "name")

    def paginate_queryset(self, queryset, page_size):
        try:
            return super(ProjectListView, self).paginate_queryset(queryset, page_size)
        except Http404:
            self.kwargs["page"] = 1  # return page 1 instead
            return super(ProjectListView, self).paginate_queryset(queryset, page_size)


def _pipelines_queryset_for_project(
    slug,
    search_query="",
    raw_filter="all",
    flagged_filter="all",
    downstream_filter="all",
):
    queryset = (
        Pipeline.objects.filter(project__slug=slug)
        .annotate(
            n_raw_files=Count("rawfile", distinct=True),
            n_downstream=Count(
                "rawfile",
                filter=Q(rawfile__use_downstream=True),
                distinct=True,
            ),
            n_flagged=Count(
                "rawfile",
                filter=Q(rawfile__flagged=True),
                distinct=True,
            ),
        )
    )

    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(slug__icontains=search_query)
        )

    if raw_filter == "with":
        queryset = queryset.filter(n_raw_files__gt=0)
    elif raw_filter == "without":
        queryset = queryset.filter(n_raw_files=0)

    if flagged_filter == "flagged":
        queryset = queryset.filter(n_flagged__gt=0)
    elif flagged_filter == "clean":
        queryset = queryset.filter(n_flagged=0)

    if downstream_filter == "with":
        queryset = queryset.filter(n_downstream__gt=0)
    elif downstream_filter == "without":
        queryset = queryset.filter(n_downstream=0)

    return queryset.order_by("name")


def _user_can_access_project(user, project):
    if user.is_staff or user.is_superuser:
        return True
    if project.created_by_id == user.id:
        return True
    return project.users.filter(pk=user.id).exists()


@login_required
def project_detail_view(request, slug):
    search_query = request.GET.get("q", "").strip()
    raw_filter = request.GET.get("raw", "all")
    flagged_filter = request.GET.get("flagged", "all")
    downstream_filter = request.GET.get("downstream", "all")
    maxquant_pipelines = _pipelines_queryset_for_project(
        slug,
        search_query=search_query,
        raw_filter=raw_filter,
        flagged_filter=flagged_filter,
        downstream_filter=downstream_filter,
    )

    page = request.GET.get("page", 1)
    paginator = Paginator(maxquant_pipelines, settings.PAGINATE)

    try:
        maxquant_pipelines = paginator.page(page)
    except PageNotAnInteger:
        maxquant_pipelines = paginator.page(1)
    except EmptyPage:
        maxquant_pipelines = paginator.page(paginator.num_pages)

    project = get_object_or_404(Project, slug=slug)
    if not _user_can_access_project(request.user, project):
        return HttpResponseForbidden("You do not have access to this project.")

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "object": project,
        "home_title": settings.HOME_TITLE,
        "maxquant_pipelines": maxquant_pipelines,
        "pipeline_search_query": search_query,
        "pipeline_raw_filter": raw_filter,
        "pipeline_flagged_filter": flagged_filter,
        "pipeline_downstream_filter": downstream_filter,
        "pipeline_querystring": query_params.urlencode(),
    }
    return render(request, "project/project_detail.html", context)


@login_required
def project_pipelines_download(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if not _user_can_access_project(request.user, project):
        return HttpResponseForbidden("You do not have access to this project.")
    pipelines = Pipeline.objects.filter(project=project).order_by("name")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{project.slug}_pipelines_summary.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["project", "pipeline_id", "pipeline_name", "description", "n_raw_files"])
    for pipeline in pipelines:
        writer.writerow(
            [
                project.name,
                pipeline.id,
                pipeline.name,
                pipeline.description,
                pipeline.n_files,
            ]
        )
    return response
