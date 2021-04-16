from django.views import generic
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings 

from .models import Project

class ListView(LoginRequiredMixin, generic.ListView):
    model = Project 
    login_url = '/accounts/login/'

    def get_queryset(self):
        projects = Project.objects.all().order_by('created').reverse()
        return projects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['home_title'] = settings.HOME_TITLE
        return context


class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Project
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = context['project']

        raw_files = RawFile.objects.filter(project=project)
        context['raw_files'] = raw_files

        maxquant_runs = MaxQuantResult.objects.filter(project=project)
        context['maxquant_runs'] = maxquant_runs

        maxquant_setups = ProteomicsPipeline.objects.filter(project=project)
        context['maxquant_setups'] = maxquant_setups
        context['home_title'] = settings.HOME_TITLE
        return context