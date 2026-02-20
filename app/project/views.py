from django.views.generic import ListView

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import Http404, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

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
        return Project.objects.all().order_by("name")

    def paginate_queryset(self, queryset, page_size):
        try:
            return super(ProjectListView, self).paginate_queryset(queryset, page_size)
        except Http404:
            self.kwargs["page"] = 1  # return page 1 instead
            return super(ProjectListView, self).paginate_queryset(queryset, page_size)


def project_detail_view(request, slug):

    # Pattern to store form data in session
    # to make pagination work with search form
    if not request.method == "POST":
        if "search-pipelines" in request.session:
            request.POST = request.session["search-pipelines"]
            request.method = "POST"
        else:
            form = SearchPipeline(request.POST)
            maxquant_pipelines = Pipeline.objects.filter(project__slug=slug)

    if request.method == "POST":
        request.session["search-pipelines"] = request.POST
        form = SearchPipeline(request.POST)
        if form.is_valid():
            maxquant_pipelines = Pipeline.objects.filter(
                project__slug=slug,
                name__iregex=form.cleaned_data["regex"],
            )

    page = request.GET.get("page", 1)
    paginator = Paginator(maxquant_pipelines, settings.PAGINATE)

    try:
        maxquant_pipelines = paginator.page(page)
    except PageNotAnInteger:
        maxquant_pipelines = paginator.page(1)
    except EmptyPage:
        maxquant_pipelines = paginator.page(paginator.num_pages)

    context = {
        "object": Project.objects.get(slug=slug),
        "home_title": settings.HOME_TITLE,
        "form": form,
        "maxquant_pipelines": maxquant_pipelines,
    }
    return render(request, "project/project_detail.html", context)


def project_pipelines_download(request, slug):
    project = Project.objects.get(slug=slug)
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
