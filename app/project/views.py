from django.views.generic import ListView

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q

from .models import Project
from .forms import SearchPipeline

from maxquant.models import Pipeline
import csv


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    login_url = "/accounts/login/"
    paginate_by = settings.PAGINATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home_title"] = settings.HOME_TITLE
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = (
            Project.objects
            .annotate(
                n_pipelines=Count("pipeline", distinct=True),
                n_raw_files=Count("pipeline__rawfile", distinct=True),
                n_members=Count("users", distinct=True),
            )
            .order_by("name")
        )
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        return queryset.filter(
            Q(created_by_id=user.id) | Q(users=user)
        ).distinct()

    def paginate_queryset(self, queryset, page_size):
        try:
            return super(ProjectListView, self).paginate_queryset(queryset, page_size)
        except Http404:
            self.kwargs["page"] = 1  # return page 1 instead
            return super(ProjectListView, self).paginate_queryset(queryset, page_size)


def _pipelines_queryset_for_project(slug, regex=None):
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
        .order_by("name")
    )
    if regex:
        queryset = queryset.filter(name__iregex=regex)
    return queryset


def _user_can_access_project(user, project):
    if user.is_staff or user.is_superuser:
        return True
    if project.created_by_id == user.id:
        return True
    return project.users.filter(pk=user.id).exists()


@login_required
def project_detail_view(request, slug):

    # Pattern to store form data in session
    # to make pagination work with search form
    if not request.method == "POST":
        if "search-pipelines" in request.session:
            request.POST = request.session["search-pipelines"]
            request.method = "POST"
        else:
            form = SearchPipeline(request.POST)
            maxquant_pipelines = _pipelines_queryset_for_project(slug)

    if request.method == "POST":
        request.session["search-pipelines"] = request.POST
        form = SearchPipeline(request.POST)
        if form.is_valid():
            maxquant_pipelines = _pipelines_queryset_for_project(
                slug,
                regex=form.cleaned_data["regex"],
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

    context = {
        "object": project,
        "home_title": settings.HOME_TITLE,
        "form": form,
        "maxquant_pipelines": maxquant_pipelines,
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
