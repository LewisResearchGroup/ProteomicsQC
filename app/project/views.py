from django.views import generic
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from .models import Project
from maxquant.models import MaxQuantPipeline


class ListView(LoginRequiredMixin, generic.ListView):
    model = Project
    login_url = "/accounts/login/"
    paginate_by = 100

    def get_queryset(self):
        projects = Project.objects.all().order_by("name")  # .reverse()
        return projects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home_title"] = settings.HOME_TITLE
        return context


class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Project
    login_url = "/accounts/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = context["project"]
        proteomics_pipelines = MaxQuantPipeline.objects.filter(project=project)
        context["maxquant_pipelines"] = proteomics_pipelines
        context["home_title"] = settings.HOME_TITLE
        return context
