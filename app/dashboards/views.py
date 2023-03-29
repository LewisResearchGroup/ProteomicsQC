from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings as conf_settings


@login_required(login_url="/accounts/login")
def dashboard(request):
    context = {"home_title": conf_settings.HOME_TITLE}
    return render(request, "dashboard/dashboard.html", context)
