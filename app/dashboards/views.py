from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings as conf_settings


@login_required(login_url='/accounts/login') 
def proteomics_dashboard_view(request):
    context = {'home_title': conf_settings.HOME_TITLE}
    return render(request, 'dashboards/proteomics_dashboard.html', context)
