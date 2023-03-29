from django.views.generic import ListView
from django.views.generic.edit import FormMixin

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Project
from .forms import SearchProject, SearchPipeline

from maxquant.models import Pipeline



class ProjectListView(LoginRequiredMixin, FormMixin, ListView):
    model = Project
    login_url = "/accounts/login/"
    paginate_by = settings.PAGINATE

    def get_form(self):
        return SearchProject()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home_title"] = settings.HOME_TITLE
        return context

    def get_queryset(self, *args, **kwargs):
        return Project.objects.all()

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset(*args, **kwargs)
        form = SearchProject(request.POST)
        request.session["search-projects"] = request.POST
        if form.is_valid():
            projects = Project.objects.filter(name__iregex=form.cleaned_data["regex"])
        self.object_list = projects
        context = self.get_context_data(object_list=projects, form=form)
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        if "search-projects" in request.session:
            request.POST = request.session["search-projects"]
            request.method = "POST"
            return self.post(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

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
